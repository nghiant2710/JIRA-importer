# Constant Class

class User:
    name='name'
    fullname='fullname'
    email='email'
    groups='groups'

class Project:
    #Attributes
    name='name'
    key='key'
    description='description'

    class Component:
        name='name'
        lead='lead'
        description='description'

    class Version:
        name='name'
        released='released'
        releasedData='releasedData'

    class Issue:
        priority='priority'
        description='description'
        status='status'
        reporter='reporter'
        labels='labels'
        watchers='watchers'
        issueType='issueType'
        resolution='resolution'
        created='created'
        updated='updated'
        affectedVersions='affectedVersions'
        summary='summary'
        assignee='assignee'
        fixedVersions='fixedVersions'
        externalId='externalId'
        history='history'
        comments='comments'
        customFieldValues='customFieldValues'
        components='components'
        class Comment:
            body='body'
            author='author'
            created='created'


