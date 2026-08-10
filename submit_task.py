import os
import sys

def submit():
    from BioactivityDataAcquisition.scripts.engineering.qa.__main__ import main
    # Fallback to pure git push if the mcp doesn't provide a 'submit' tool
    print("Please use the 'submit' MCP tool directly.")

if __name__ == "__main__":
    submit()
