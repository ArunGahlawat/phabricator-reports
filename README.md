# Phabricator-Reports

Generate phabricator reports based on project name.
Uses Phabricator's Conduit api to fetch project details and get all tasks tagged to it
<br>Tasks has linked differential revisions and inline comments are linked to revisions as transactions of type 'inline'

###Usage
- create config.py using config.py.sample file
- update phabricator host and conduit api token ( Get from Phabricator -> User Settings -> Conduit API Tokens -> Generate)
- create reports/export.json using reports/export.json.sample
 
####To generate report:
>  python3 generate_report.py -p "project name"

For help:
> python3 generate_report.py -h