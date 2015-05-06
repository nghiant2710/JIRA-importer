# Trello JSON Parser for JIRA

This script will parse exported JSON file from Trello into importable JSON file for JIRA.

### Configuration File

* inputfilepath: Path to JSON file from Trello
* outputfilepath: Output file path
* issueswithchecklist: Specify path to file contains issues that have checklist, example: issues_with_checklist.txt
* missinginfoissue: Specify path to missing information issue file, example: missing_info_issues.txt
* projectKey: Specify JIRA project key, example: RESINDEV

### Usage

__Note:__ JIRA won't import existed issues and workflow for project. In the first time, we should create new project and set resin workflow for it before import. Project key in configuration file will specify the target project to import.

* Export Trello to JSON
* Edit `config.ini` file
* Execute `python TrelloParser.py`
* Access `Administration/System/External System Import` to import new JSON file