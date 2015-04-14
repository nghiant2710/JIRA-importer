import json
import jira_models
import sys


STATUS = ['Doing', 'Waiting for review', 'Waiting for Staging', 'Waiting for test', 'Waiting for Production']
LABEL_LIST = ['api', 'pinejs', 'devices', 'meta-resin', 'supervisor', 'ui', 'Devices', 'VPN', 'security',
              'builder' 'img-maker', 'resin-api', 'frontend', 'meta-resin', 'analytics', 'resin-img', 'resin-cli', 'cli',
              'registry', 'gitlab', 'e2e', 'yocto', 'cloud_formation']

# All action types on trello: https://trello.com/docs/api/card/index.html#get-1-cards-card-id-or-shortlink-actions
ACTION_TYPE = ['createCard', 'commentCard']
USER_ROLES={
    1:'jira-developers',
    2:'jira-users'
}
ISSUE_TYPE={
    1:'Bug',
    2:'Task',
    3:'Improvement',
    4:'New Feature'
}

class TrelloJSONParser:
    data = {}

    # labels contains all list's name in Trello with its id
    labels = {}
    # checklists contains all checklists of cards in Trello
    checklists = {}
    # actions contains actions with action type in ACTION_TYPE
    # dict_actions maps cardShortID with its actions
    actions = {}
    dict_actions = {}
    # users contains list of members in Trello
    users = []

    def __init__(self, path):
        self.data = json.loads(open(path).read())
        self.import_trello_list()
        self.import_checklist()
        self.import_actions()
        self.import_users()

    def import_trello_list(self):
        for temp in self.data['lists']:
            if temp['name'] not in STATUS:
                self.labels[temp['id']] = temp['name']

    def import_checklist(self):
        for temp in self.data['checklists']:
            id = temp['id']
            contents = {temp['idCard']: 'CARD_ID'}
            for checkItem in temp['checkItems']:
                contents[checkItem['name']] = checkItem['state']
                self.checklists[id] = contents

    def import_actions(self):
        for temp in self.data['actions']:
            if temp['type'] in ACTION_TYPE:
                self.actions[temp['id']] = temp
                card_short_id = temp['data']['card']['idShort']
                if self.dict_actions.has_key(card_short_id):
                    self.dict_actions[card_short_id].append(temp['id'])
                else:
                    self.dict_actions[card_short_id] = [temp['id']]

    def import_users(self):
        for temp in self.data['members']:
            user = {}
            user[jira_models.User.name] = temp['username']
            user[jira_models.User.fullname] = temp['fullName']
            user['id'] = temp['id']
            self.users.append(user)

    def parse_user(self):
        users_obj = []
        for temp in self.users:
            user = {}
            user[jira_models.User.name] = temp[jira_models.User.name]
            user[jira_models.User.fullname] = temp[jira_models.User.fullname]
            user[jira_models.User.groups] = [USER_ROLES[1]]
            users_obj.append(user)
        return users_obj

    def parse_project(self,key):
        result = []
        pj_obj = {}
        pj_obj[jira_models.Project.name] = self.data['name']
        pj_obj[jira_models.Project.key] = key
        pj_obj[jira_models.Project.description] = self.data['desc']
        result.append(pj_obj)
        return result

    def parse_issue(self):
        issues_obj = []
        for temp in self.data['cards']:
            if not temp['closed']:
                issue = {}
                card_short_id = temp['idShort']
                issue[jira_models.Project.Issue.summary] = temp['name']
                issue[jira_models.Project.Issue.description] = temp['desc']
                issue[jira_models.Project.Issue.externalId] = card_short_id
                # Card has actions. Many cards are lack of information in json file
                if self.dict_actions.has_key(card_short_id):
                    for actionId in self.dict_actions[card_short_id]:
                        if self.actions[actionId]['type'] == 'createCard':
                            issue[jira_models.Project.Issue.created] = self.actions[actionId]['date']
                            issue[jira_models.Project.Issue.reporter] = self.actions[actionId]['memberCreator']['username']
                            break
                # generate labels
                issue[jira_models.Project.Issue.labels] = self.generate_issue_label(temp)
                # add comments
                issue[jira_models.Project.Issue.comments] = self.generate_issue_comment(temp)
                # set members which is a custom field instead of assignee (can only one person as assignee)
                issue[jira_models.Project.Issue.customFieldValues] = self.generate_issue_member(temp)
                # set issue type
                if self.verify_bug(temp):
                    issue[jira_models.Project.Issue.issueType] = ISSUE_TYPE[1]
                else:
                    issue[jira_models.Project.Issue.issueType] = ISSUE_TYPE[2]
                issues_obj.append(issue)
        return issues_obj

    def generate_issue_label(self, card):
        labels = []
        str_name = card['name'].encode('utf-8')
        for keyword in LABEL_LIST:
            if str_name.lower().find('[' + keyword.lower() + ']') > -1:
                labels.append(keyword)
        if card['idList'] in self.labels.keys():
            labels.append(self.labels[card['idList']])
        return labels

    def generate_issue_comment(self,card):
        comments = []
        card_short_id = card['idShort']
        if self.dict_actions.has_key(card_short_id):
            for actionId in self.dict_actions[card_short_id]:
                if self.actions[actionId]['type'] == 'commentCard':
                    comment = {}
                    comment[jira_models.Project.Issue.Comment.author] = self.actions[actionId]['memberCreator']['username']
                    comment[jira_models.Project.Issue.Comment.created] = self.actions[actionId]['date']
                    comment[jira_models.Project.Issue.Comment.body] = self.actions[actionId]['data']['text']
                    comments.append(comment)
        return comments


    def generate_issue_member(self,card):
        members = []
        pic_names = []
        for pic in card['idMembers']:
            for x in self.users:
                if pic == x['id']:
                    pic_names.append(x[jira_models.User.name])
        members.append({
            "fieldName": "Members",
            "fieldType": "com.atlassian.jira.plugin.system.customfieldtypes:multiuserpicker",
            "value": pic_names
        })
        return members

    def verify_bug(self,card):
        for label in card['labels']:
            if label['name'] == 'BUG':
                return True
        return False

json_file_path = sys.argv[1]
output_file_path = sys.argv[2]
parser = TrelloJSONParser(json_file_path)
obj = {}
obj['users'] = parser.parse_user()
obj['projects'] = parser.parse_project('RESINDEV')
obj['projects'][0]['issues'] = parser.parse_issue()

with open(output_file_path, 'w') as outfile:
    json.dump(obj, outfile)