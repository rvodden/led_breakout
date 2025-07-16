# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a KiCad PCB design project for an LED breakout board. The project uses KiBot for automated fabrication file generation and includes CI/CD workflows for design rule checks and production file generation.

## Architecture

The project is organized with:
- **Main design files**: `LED Breakout.kicad_sch` (main schematic), `LED Breakout.kicad_pcb` (PCB layout)
- **Sub-schematics**: `led.kicad_sch` and `switch.kicad_sch` for modular design
- **Automation**: KiBot configuration files in `.kibot/` directory for ERC/DRC checks and production file generation
- **Utils**: Python utilities in `utils/` directory for CI/CD integration

## Common Commands

### KiBot Commands (Design Rule Checks)
```bash
# Run ERC/DRC checks
kibot -q --log output/kibot.log -c .kibot/erc-drc.kibot.yaml --schema "LED Breakout.kicad_sch" --board "LED Breakout.kicad_pcb"

# Generate production files for JLCPCB
kibot -q --log output/kibot.log -c .kibot/production.kibot.yaml --schema "LED Breakout.kicad_sch" --board "LED Breakout.kicad_pcb" -d output/jlcpcb

# Generate Interactive BOM
kibot -q --log output/kibot.log -c .kibot/ibom.kibot.yaml --board "LED Breakout.kicad_pcb" -d ibom_output
```

### Python Utilities
```bash
# Convert KiCad ERC/DRC output to xUnit XML for CI/CD
python3 utils/kicad2xunit.py input_file.txt -o output/erc_output.xml

# Pipe KiBot output directly to xUnit converter
kibot ... | python3 utils/kicad2xunit.py > output/erc_output.xml
```

## CI/CD Workflows

The project includes two GitHub Actions workflows:

1. **ERC/DRC Check** (`.github/workflows/erc-drc-check.yml`): Runs on PRs to validate design rules
2. **Production Release** (`.github/workflows/production-release.yml`): Runs on main branch to generate production files

## Key Configuration Files

- `.kibot/erc-drc.kibot.yaml`: ERC/DRC check configuration with PCB print generation
- `.kibot/production.kibot.yaml`: Production file generation (Gerbers, drill files, BOM, pick & place)
- `.kibot/ibom.kibot.yaml`: Interactive BOM generation for GitHub Pages
- `fabrication-toolkit-options.json`: Fabrication toolkit settings

## Output Structure

- `output/`: ERC/DRC reports and logs
- `output/jlcpcb/`: Production files for JLCPCB manufacturing
- `output/review/`: PCB assembly PDFs for design review
- `output/ibom/`: Interactive BOM files for web deployment

## Development Notes

- The project uses hierarchical schematics with separate LED and switch sub-sheets
- All components include LCSC part numbers for JLCPCB assembly
- The kicad2xunit.py utility converts KiCad output to xUnit XML format for CI/CD integration
- Production files are automatically generated and deployed to GitHub Pages on main branch pushes