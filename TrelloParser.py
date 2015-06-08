import json
import jira_models
import sys
import ConfigParser


STATUS = {
    'To Do':'TO DO',
    'Waiting for Implementation':'REVIEWING',
    'On going tasks (don\'t end)':'IN PROGRESS',
    'Done':'DONE'
}
LABEL_LIST = {
    'blue':'Icebox',
    'green':'Low Priority',
    'orange':'High Priority'
}

COMPONENT_LIST = ["Demos","Documentation", "Social media", "Mailing list/Newsletter", "Website", "Media", "Events", "Swag", "Services"]

PRIORITY_LIST = {
    'Highest':[],
    'Medium':[],
    'Low':[]
}


# All action types on trello: https://trello.com/docs/api/card/index.html#get-1-cards-card-id-or-shortlink-actions
ACTION_TYPE = ['createCard', 'commentCard']
USER_ROLES={
    1:'jira-developers',
    2:'jira-users'
}
ISSUE_TYPE={
    'R&D':'Feature',
    'Proposed Features':'Feature',
    'Completed Features':'Feature',
    1:'Bug',
    2:'Task',
    3:'Improvement',
}

CONFIG_PATH='config.ini'
CONFIG_KEYS={
    1:'inputfilepath',
    2:'outputfilepath',
    3:'projectkey',
    4:'issueswithchecklist',
    5:'missinginfoissue'
}

class TrelloJSONParser:
    data = {}

    # labels contains all list's name in Trello with its id
    labels = {}
    status_labels = {}
    board_labels={}
    # contains all cards with checklists in Trello
    issue_with_checklists = {}
    # actions contains actions with action type in ACTION_TYPE
    # dict_actions maps cardShortID with its actions
    actions = {}
    dict_actions = {}
    # users contains list of members in Trello
    users = {}
    jira_users = {}
    # list contains all missing info cards in Trello
    missing_info_issue={}

    def __init__(self, path):
        self.data = json.loads(open(path).read())
        self.jira_users = json.loads(open('users.json').read())
        for temp in self.jira_users['users']:
            self.jira_users[temp[jira_models.User.fullname]] = temp[jira_models.User.name]
        self.import_trello_list()
        #self.import_checklist()
        self.import_actions()
        self.import_users()
        self.import_labels()

    def import_trello_list(self):
        for temp in self.data['lists']:
            if temp['name'] not in STATUS.keys():
                self.labels[temp['id']] = temp['name']
            else:
                self.status_labels[temp['id']] = temp['name']

    #def import_checklist(self):
    #    for temp in self.data['checklists']:
    #        id = temp['id']
    #        contents = {}
    #        for checkItem in temp['checkItems']:
    #            contents[checkItem['name']] = checkItem['state']
    #            self.checklists[id] = contents

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
            full_name = temp['fullName']

            if full_name == 'Petros Aggelatos':
                full_name = 'Petros Angelatos'
            elif full_name == 'Aleksis Brezas':
                full_name = 'Alexis Brezas'

            user[jira_models.User.fullname] = full_name
            if full_name not in self.jira_users.keys():
                user[jira_models.User.name] = full_name
            else:
                user[jira_models.User.name] = self.jira_users[full_name]            
            user['id'] = temp['id']
            self.users[temp['id']]=user

    def import_labels(self):
        for temp in self.data['labels']:
            if temp['color'] in LABEL_LIST.keys():
                self.board_labels[temp['id']]=temp['color']

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

    def parse_component(self):
        return COMPONENT_LIST

    def parse_issue(self):
        issues_obj = []
        for temp in self.data['cards']:
            if not temp['closed']:
                issue = {}
                missing_info_check= 0
                card_short_id = temp['idShort']
                title = temp['name'].encode('utf-8')
                issue[jira_models.Project.Issue.summary] = self.generate_issue_summary(temp)
                issue[jira_models.Project.Issue.description] = temp['desc']
                issue[jira_models.Project.Issue.externalId] = card_short_id
                # Card has actions. Many cards are lack of information in json file
                if self.dict_actions.has_key(card_short_id):
                    for actionId in self.dict_actions[card_short_id]:
                        if self.actions[actionId]['type'] == 'createCard':
                            issue[jira_models.Project.Issue.created] = self.actions[actionId]['date']
                            if self.actions[actionId]['idMemberCreator'] in self.users.keys():
                                issue[jira_models.Project.Issue.reporter] = self.users[self.actions[actionId]['idMemberCreator']][jira_models.User.name]
                            missing_info_check = 1
                            break
                # check if card lost info
                if missing_info_check == 0:
                    self.missing_info_issue[temp['id']] = title
                # check if card has checklist
                if len(temp['idChecklists']) >0:
                    self.issue_with_checklists[temp['id']] = title
                # generate labels
                issue[jira_models.Project.Issue.labels] = self.generate_issue_label(temp)
                # add comments
                issue[jira_models.Project.Issue.comments] = self.generate_issue_comment(temp)

                # set assignee that is the first member of card
                for pic in temp['idMembers']:
                    if self.users.has_key(pic):
                        issue[jira_models.Project.Issue.assignee] = self.users[pic][jira_models.User.name]

                # set members which is a custom field instead of assignee (can only one person as assignee)
                issue[jira_models.Project.Issue.customFieldValues] = self.generate_issue_custom_content(temp)
                # set issue type
                #issue[jira_models.Project.Issue.issueType] = self.generate_issue_type(temp)
                issue[jira_models.Project.Issue.issueType] = ISSUE_TYPE[2]
                # set issue state
                state = self.generate_issue_state(temp)
                if state != -1:
                    issue[jira_models.Project.Issue.status] = state
                if state == STATUS['Done']:
                    issue[jira_models.Project.Issue.resolution] = 'Resolved'
                # set issue components
                issue[jira_models.Project.Issue.components] = self.generate_issue_component(temp)
                # set priority
                #issue[jira_models.Project.Issue.priority] = self.generate_issue_priority(temp)
                issue[jira_models.Project.Issue.priority]= 'Low'

                issues_obj.append(issue)
        return issues_obj

    def generate_issue_label(self, card):
        labels = []
        for label in card['idLabels']:
            if label in self.board_labels.keys():
                labels.append(LABEL_LIST[self.board_labels[label]])
        return labels


    def generate_issue_component(self,card):
        components = []
        if card['idList'] in self.labels.keys():
            if self.labels[card['idList']] in COMPONENT_LIST:
                components.append(self.labels[card['idList']])
        return components

    def generate_issue_summary(self,card):
        title = card['name'].encode('utf-8')
        for keyword in COMPONENT_LIST:
            if title.lower().find('[resin-' + keyword.lower() + ']') > -1 or title.lower().find('[' + keyword.lower() + ']') > -1:
                title = title[(title.lower().rfind(']')+1):]
        if title.lower().find('[meta-resin]') > -1:
            title = title[(title.lower().rfind(']')+1):]
        return title


    def generate_issue_state(self,card):
        if card['idList'] in self.status_labels.keys():
            return STATUS[self.status_labels[card['idList']]]
        return -1

    #def generate_issue_priority(self,card):
        #for priority in PRIORITY_LIST:
        #    for group in PRIORITY_LIST[priority]:
        #        if self.labels.has_key(card['idList']) and self.labels[card['idList']] == group:
        #            return priority
        #        if self.status_labels.has_key(card['idList']) and self.status_labels[card['idList']] == group:
        #            return priority
        #return 'Low'


    def generate_issue_comment(self,card):
        comments = []
        card_short_id = card['idShort']
        if self.dict_actions.has_key(card_short_id):
            for actionId in self.dict_actions[card_short_id]:
                if self.actions[actionId]['type'] == 'commentCard':
                    comment = {}
                    if self.actions[actionId]['idMemberCreator'] in self.users.keys():
                        comment[jira_models.Project.Issue.Comment.author] = self.users[self.actions[actionId]['idMemberCreator']][jira_models.User.name]
                    comment[jira_models.Project.Issue.Comment.created] = self.actions[actionId]['date']
                    comment[jira_models.Project.Issue.Comment.body] = self.actions[actionId]['data']['text']
                    comments.append(comment)
        return comments

    def generate_issue_custom_content(self,card):
        custom_contents = []
        pic_names = []
        for pic in card['idMembers']:
            if self.users.has_key(pic):
                pic_names.append(self.users[pic][jira_models.User.name])
        custom_contents.append({
            "fieldName": "Members",
            "fieldType": "com.atlassian.jira.plugin.system.customfieldtypes:multiuserpicker",
            "value": pic_names
        })
        #contents = []
        #for id in card['idChecklists']:
        #    if self.checklists.has_key(id):
        #        for x in self.checklists[id].keys():
        #            contents.append(x )
        #custom_contents.append({
        #    "fieldName": "Issue Checklist",
        #    "fieldType": "com.atlassian.jira.plugin.system.customfieldtypes:multicheckboxes",
        #    "value": contents
        #})
        return custom_contents

    #def generate_issue_type(self,card):
        #if self.status_labels.has_key(card['idList']) and self.status_labels[card['idList']] in ISSUE_TYPE.keys():
        #    return ISSUE_TYPE[self.status_labels[card['idList']]]
        #if self.labels.has_key(card['idList']) and self.labels[card['idList']] in ISSUE_TYPE.keys():
        #    return ISSUE_TYPE[self.labels[card['idList']]]
        #return ISSUE_TYPE[2]

    def export_issue_with_checklists(self,path):
        f = open(path,'w')
        f.write('Cards with checklist:\n')
        for issue in self.issue_with_checklists.values():
            f.write(issue+'\n')
        f.close()

    def export_missing_info_issue(self,path):
        f = open(path,'w')
        f.write('Missing Info Cards:\n')
        for issue in self.missing_info_issue.values():
            f.write(issue+'\n')
        f.close()



def read_config_section(section):
    config_reader = ConfigParser.ConfigParser()
    config_reader.read(CONFIG_PATH)
    config_data = {}
    options = config_reader.options(section)
    for option in options:
        try:
            config_data[option] = config_reader.get(section, option)
        except:
            config_data[option] = None
    return config_data


config = read_config_section('Parameters')
json_file_path = config[CONFIG_KEYS[1]]
output_file_path = config[CONFIG_KEYS[2]]
checklist_file = config[CONFIG_KEYS[4]]
missing_file = config[CONFIG_KEYS[5]]
parser = TrelloJSONParser(json_file_path)
obj = {}

#obj['users'] = parser.parse_user()
obj['projects'] = parser.parse_project(config[CONFIG_KEYS[3]])
obj['projects'][0]['components'] = parser.parse_component()
obj['projects'][0]['issues'] = parser.parse_issue()

parser.export_issue_with_checklists(checklist_file)
parser.export_missing_info_issue(missing_file)

with open(output_file_path, 'w') as outfile:
    json.dump(obj, outfile)
