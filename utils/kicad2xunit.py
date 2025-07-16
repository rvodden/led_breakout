#!/usr/bin/env python3
"""
KiCad ERC/DRC to xUnit XML converter

This script parses KiCad ERC/DRC output and converts it to xUnit XML format
for integration with CI/CD systems. Supports both errors and warnings.
"""

import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Dict, Any
import argparse


class ERCIssue:
    """Represents a single ERC error or warning"""
    def __init__(self, severity: str, issue_type: str, message: str, location: str, context: str):
        self.severity = severity  # "ERROR" or "WARNING"
        self.issue_type = issue_type
        self.message = message
        self.location = location
        self.context = context  # Sheet info or Check info
    
    def __str__(self):
        return f"{self.severity}({self.issue_type}): {self.message} at {self.location} ({self.context})"


class ERCParser:
    """Parser for KiCad ERC output"""
    
    def __init__(self):
        self.issues = []
        self.total_errors = 0
        self.total_warnings = 0
    
    def parse(self, content: str) -> List[ERCIssue]:
        """Parse the ERC/DRC output content"""
        lines = content.strip().split('\n')
        current_issue = None
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
                
            # Parse warning/error lines
            if line.startswith('WARNING:') or line.startswith('ERROR:'):
                # Extract severity and issue type
                if line.startswith('WARNING:'):
                    severity = 'WARNING'
                    # Look for issue type in parentheses like (W145)
                    issue_type_match = re.search(r'\(([^)]+)\)', line)
                    if issue_type_match:
                        issue_type = issue_type_match.group(1)
                        # Extract message after the issue type
                        message = re.sub(r'^WARNING:\([^)]+\)\s*', '', line)
                        # Remove trailing context info
                        message = re.sub(r'\s*\([^)]*kibot[^)]*\)$', '', message)
                    else:
                        issue_type = 'UNKNOWN'
                        message = line[8:]  # Remove 'WARNING:'
                        
                elif line.startswith('ERROR:'):
                    severity = 'ERROR'
                    # Handle different error formats
                    if '(' in line and ')' in line:
                        issue_type_match = re.search(r'\(([^)]+)\)', line)
                        if issue_type_match:
                            issue_type = issue_type_match.group(1)
                            message = re.sub(r'^ERROR:\([^)]+\)\s*', '', line)
                        else:
                            issue_type = 'ERROR'
                            message = line[6:]  # Remove 'ERROR:'
                    else:
                        issue_type = 'ERROR'
                        message = line[6:]  # Remove 'ERROR:'
                    
                    # Remove trailing context info
                    message = re.sub(r'\s*\([^)]*kibot[^)]*\)$', '', message)
                
                # Create the issue (location and context will be added later)
                current_issue = {
                    'severity': severity,
                    'issue_type': issue_type,
                    'message': message,
                    'location': '',
                    'context': ''
                }
                
            # Parse location lines that start with @ 
            elif line.startswith('@') and current_issue:
                # Extract coordinates and component info
                location_match = re.search(r'@\(([^)]+)\):\s*(.+)', line)
                if location_match:
                    coordinates = location_match.group(1)
                    component_info = location_match.group(2)
                    current_issue['location'] = coordinates
                    current_issue['context'] = component_info
                    
                    # Create the ERCIssue object and add to list
                    issue = ERCIssue(
                        current_issue['severity'],
                        current_issue['issue_type'], 
                        current_issue['message'],
                        current_issue['location'],
                        current_issue['context']
                    )
                    self.issues.append(issue)
                    
                    # Update counters
                    if current_issue['severity'] == 'ERROR':
                        self.total_errors += 1
                    else:
                        self.total_warnings += 1
                        
                    current_issue = None
                    
            # Handle Check: lines that might provide additional context
            elif line.startswith('Check:') and current_issue:
                current_issue['context'] = line[6:].strip()  # Remove 'Check:'
        
        return self.issues


class xUnitGenerator:
    """Generates xUnit XML from ERC errors"""
    
    def __init__(self, parser: ERCParser):
        self.parser = parser
    
    def generate_xml(self, output_file: str | None = None) -> str:
        """Generate xUnit XML output"""
        # Create root element
        testsuites = ET.Element("testsuites")
        testsuites.set("name", "KiCad ERC")
        testsuites.set("tests", str(len(self.parser.issues)))
        testsuites.set("failures", str(len(self.parser.issues)))
        testsuites.set("errors", "0")
        testsuites.set("time", "0")
        testsuites.set("timestamp", datetime.now().isoformat())
        
        # Create testsuite element
        testsuite = ET.SubElement(testsuites, "testsuite")
        testsuite.set("name", "ERC Checks")
        testsuite.set("tests", str(len(self.parser.issues)))
        testsuite.set("failures", str(len(self.parser.issues)))
        testsuite.set("errors", "0")
        testsuite.set("time", "0")
        testsuite.set("timestamp", datetime.now().isoformat())
        
        # Add properties
        properties = ET.SubElement(testsuite, "properties")
        prop = ET.SubElement(properties, "property")
        prop.set("name", "total_erc_errors")
        prop.set("value", str(self.parser.total_errors))
        
        # Create test cases for each error
        for i, issue in enumerate(self.parser.issues):
            testcase = ET.SubElement(testsuite, "testcase")
            testcase.set("name", f"ERC_{issue.issue_type}_{i+1}")
            testcase.set("classname", f"ERC.{issue.issue_type}")
            testcase.set("time", "0")
            
            # Add failure element
            failure = ET.SubElement(testcase, "failure")
            failure.set("type", issue.issue_type)
            failure.set("message", issue.message)
            
            # Failure text includes location and context info
            failure_text = f"Issue Type: {issue.issue_type}\n"
            failure_text += f"Severity: {issue.severity}\n"
            failure_text += f"Message: {issue.message}\n"
            if issue.location:
                failure_text += f"Location: {issue.location}\n"
            if issue.context:
                failure_text += f"Context: {issue.context}\n"
            
            failure.text = failure_text
        
        # If no errors, add a passing test
        if not self.parser.issues:
            testcase = ET.SubElement(testsuite, "testcase")
            testcase.set("name", "ERC_NoErrors")
            testcase.set("classname", "ERC.Success")
            testcase.set("time", "0")
            
            # Update counts
            testsuite.set("tests", "1")
            testsuite.set("failures", "0")
            testsuites.set("tests", "1")
            testsuites.set("failures", "0")
        
        # Generate XML string
        xml_str = ET.tostring(testsuites, encoding='unicode')
        
        # Pretty print (basic formatting)
        xml_str = self._pretty_print_xml(xml_str)
        
        # Write to file if specified
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
                f.write(xml_str)
        
        return xml_str
    
    def _pretty_print_xml(self, xml_str: str) -> str:
        """Basic XML pretty printing"""
        try:
            import xml.dom.minidom
            dom = xml.dom.minidom.parseString(xml_str)
            return dom.toprettyxml(indent="  ")[23:]  # Remove XML declaration
        except:
            return xml_str


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Convert KiCad ERC/DRC output to xUnit XML')
    parser.add_argument('input_file', nargs='?', help='Input file containing ERC/DRC output (default: stdin)')
    parser.add_argument('-o', '--output', help='Output XML file (default: stdout)')
    
    args = parser.parse_args()
    
    # Read input
    if args.input_file:
        with open(args.input_file, 'r', encoding='utf-8') as f:
            content = f.read()
    else:
        content = sys.stdin.read()
    
    # Parse ERC/DRC output
    erc_parser = ERCParser()
    # For now, just call without debug to avoid the error
    issues = erc_parser.parse(content)
    
    # Generate xUnit XML
    xml_generator = xUnitGenerator(erc_parser)
    xml_output = xml_generator.generate_xml(args.output)
    
    # Output to stdout if no output file specified
    if not args.output:
        print('<?xml version="1.0" encoding="UTF-8"?>')
        print(xml_output)


if __name__ == "__main__":
    main()
