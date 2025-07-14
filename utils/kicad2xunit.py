#!/usr/bin/env python3
"""
KiCad ERC to xUnit XML converter

This script parses KiCad ERC output and converts it to xUnit XML format
for integration with CI/CD systems.
"""

import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Dict, Any
import argparse


class ERCError:
    """Represents a single ERC error"""
    def __init__(self, error_type: str, message: str, location: str, sheet: str):
        self.error_type = error_type
        self.message = message
        self.location = location
        self.sheet = sheet
    
    def __str__(self):
        return f"{self.error_type}: {self.message} at {self.location} (Sheet: {self.sheet})"


class ERCParser:
    """Parser for KiCad ERC output"""
    
    def __init__(self):
        self.errors = []
        self.total_errors = 0
    
    def parse(self, content: str) -> List[ERCError]:
        """Parse the ERC output and extract errors"""
        lines = content.strip().split('\n')
        
        # Find total error count - check both patterns
        error_count_patterns = [
            r'ERROR:(\d+) ERC errors detected',
            r'ERROR:ERC errors:\s*(\d+)'
        ]
        
        for line in lines:
            for pattern in error_count_patterns:
                match = re.search(pattern, line)
                if match:
                    self.total_errors = int(match.group(1))
                    break
            if self.total_errors > 0:
                break
        
        # Parse individual errors
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Skip lines that don't contain error information
            if not line or 'kibot' in line or line.startswith('ERROR:ERC errors:'):
                i += 1
                continue
            
            # Look for error type pattern - format: ERROR:(error_type) message
            error_type_match = re.search(r'ERROR:\(([^)]+)\)\s*(.*)', line)
            if error_type_match:
                error_type = error_type_match.group(1)
                message = error_type_match.group(2).strip()
                location = ""
                sheet = ""
                
                # Look for location and additional info in next line
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    # Pattern: @(coordinates): additional info
                    location_match = re.search(r'@\(([^)]+)\):\s*(.*)', next_line)
                    if location_match:
                        location = location_match.group(1)
                        additional_info = location_match.group(2).strip()
                        if additional_info:
                            message = additional_info
                        
                        # Look for sheet info in the line after location
                        if i + 2 < len(lines):
                            sheet_line = lines[i + 2].strip()
                            sheet_match = re.search(r'Sheet:\s*(.+)', sheet_line)
                            if sheet_match:
                                sheet = sheet_match.group(1).strip()
                                # Remove kibot references from sheet info
                                sheet = re.sub(r'\s*\(kibot[^)]*\)', '', sheet)
                                i += 3  # Skip all processed lines
                            else:
                                i += 2  # Skip error and location lines
                        else:
                            i += 2  # Skip error and location lines
                    else:
                        i += 1  # Skip just the error line
                else:
                    i += 1  # Skip just the error line
                
                self.errors.append(ERCError(error_type, message, location, sheet))
            else:
                i += 1
        
        return self.errors


class xUnitGenerator:
    """Generates xUnit XML from ERC errors"""
    
    def __init__(self, parser: ERCParser):
        self.parser = parser
    
    def generate_xml(self, output_file: str = None) -> str:
        """Generate xUnit XML output"""
        # Create root element
        testsuites = ET.Element("testsuites")
        testsuites.set("name", "KiCad ERC")
        testsuites.set("tests", str(len(self.parser.errors)))
        testsuites.set("failures", str(len(self.parser.errors)))
        testsuites.set("errors", "0")
        testsuites.set("time", "0")
        testsuites.set("timestamp", datetime.now().isoformat())
        
        # Create testsuite element
        testsuite = ET.SubElement(testsuites, "testsuite")
        testsuite.set("name", "ERC Checks")
        testsuite.set("tests", str(len(self.parser.errors)))
        testsuite.set("failures", str(len(self.parser.errors)))
        testsuite.set("errors", "0")
        testsuite.set("time", "0")
        testsuite.set("timestamp", datetime.now().isoformat())
        
        # Add properties
        properties = ET.SubElement(testsuite, "properties")
        prop = ET.SubElement(properties, "property")
        prop.set("name", "total_erc_errors")
        prop.set("value", str(self.parser.total_errors))
        
        # Create test cases for each error
        for i, error in enumerate(self.parser.errors):
            testcase = ET.SubElement(testsuite, "testcase")
            testcase.set("name", f"ERC_{error.error_type}_{i+1}")
            testcase.set("classname", f"ERC.{error.error_type}")
            testcase.set("time", "0")
            
            # Add failure element
            failure = ET.SubElement(testcase, "failure")
            failure.set("type", error.error_type)
            failure.set("message", error.message)
            
            # Failure text includes location and sheet info
            failure_text = f"Error Type: {error.error_type}\n"
            failure_text += f"Message: {error.message}\n"
            if error.location:
                failure_text += f"Location: {error.location}\n"
            if error.sheet:
                failure_text += f"Sheet: {error.sheet}\n"
            
            failure.text = failure_text
        
        # If no errors, add a passing test
        if not self.parser.errors:
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
    parser = argparse.ArgumentParser(description='Convert KiCad ERC output to xUnit XML')
    parser.add_argument('input_file', nargs='?', help='Input file containing ERC output (default: stdin)')
    parser.add_argument('-o', '--output', help='Output XML file (default: stdout)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    # Read input
    if args.input_file:
        with open(args.input_file, 'r', encoding='utf-8') as f:
            content = f.read()
    else:
        content = sys.stdin.read()
    
    # Parse ERC output
    erc_parser = ERCParser()
    errors = erc_parser.parse(content)
    
    if args.verbose:
        print(f"Found {len(errors)} ERC errors:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
    
    # Generate xUnit XML
    xml_generator = xUnitGenerator(erc_parser)
    xml_output = xml_generator.generate_xml(args.output)
    
    # Output to stdout if no output file specified
    if not args.output:
        print('<?xml version="1.0" encoding="UTF-8"?>')
        print(xml_output)


if __name__ == "__main__":
    main()