import os
import re
import json

import requests
import tinydb
import jenkins
import pygithub3

outputs = []
DB = tinydb.TinyDB("/mnt/db/slack.json")
JENKINS_TOKEN = os.environ.get("JENKINS_TOKEN")
JENKINS_USER = os.environ.get("JENKINS_USER", "fido")
JENKINS_USER_PASS = os.environ.get("JENKINS_USER_PASS")
JENKINS_URL = os.environ.get("JENKINS_URL")
SAGE_START_URL = os.environ.get("SAGE_START_URL")
SAGE_CLIENT_URL = os.environ.get("SAGE_CLIENT_URL", "http://somewhere.org")
SAGE_DISPLAY_URL = SAGE_CLIENT_URL + "/display.html?clientID=0"
REPOS_DIR = "/tmp/bb_repos"


def _get_local_repo(path):
    return


def _build_job(data, prno, docs=False):
    return
    # try:
    #     pr = get_pr_info(None, "yt_analysis/yt", prno)   #####
    # except urllib2.HTTPError:
    #     outputs.append([data['channel'],
    #                     "Something went wrong. Pester xarthisius"])
    #     return
    pr = {}
    author = pr['author']['display_name']
    if docs:
        msg = "will build docs for PR %i" % prno
        urls = ["%s/job/%s/build?token=%s" % (JENKINS_URL, "yt_docs",
                                              JENKINS_TOKEN)]
    else:
        msg = "will test PR %i by %s" % (prno, author)
        urls = ["%s/job/%s/build?token=%s" % (JENKINS_URL, "yt_testsuite",
                                              JENKINS_TOKEN)]
    params = [
        {'name': 'IRKMSG', 'value': msg},
        {'name': 'YT_REPO', 'value': pr['source']['repository']['full_name']},
        {'name': 'YT_REV', 'value': pr['source']['commit']['hash']},
        {'name': 'YT_DEST', 'value': pr['destination']['commit']['hash']}
    ]
    payload = {
        'json': json.dumps({'parameter': params}),
        'Submit': 'Build'
    }
    for url in urls:
        requests.post(url, data=payload)
    outputs.append([data['channel'], "job submitted"])


class FidoCommand:
    regex = None
    help_msg = None

    def __call__(self, data, outputs):
        s = self.regex(data["text"])
        if s is not None:
            if len(s.groups()) > 0:
                self.run(s.groups(), data, outputs)

    def run(self, match, data, outputs):
        pass


class FidoBuildDocs(FidoCommand):
    regex = re.compile(r'build docs for PR\s?(\d+)', re.IGNORECASE).search

    def run(self, match, data, outputs):
        _build_job(data, int(match[0]), docs=True)


class FidoTestPR(FidoCommand):
    regex = re.compile(r'test PR\s?(\d+)', re.IGNORECASE).search

    def run(self, match, data, outputs):
        _build_job(data, int(match[0]), docs=False)


class FidoGetPRInfo(FidoCommand):
    regex = re.compile(r'PR\s?(\d+)', re.IGNORECASE).search

    def run(self, match, data, outputs):
        try:
            gh = pygithub3.Github()
            pr = gh.pull_requests.get(
                int(match[0]), user='yt-project', repo='yt')
            outputs.append([data['channel'], pr.html_url])
        except pygithub3.exceptions.NotFound:
            pass


class FidoGetIssueInfo(FidoCommand):
    regex = re.compile(r'#(\d+)').search

    def run(self, match, data, outputs):
        try:
            gh = pygithub3.Github()
            issue = gh.issues.get(int(match[0]), user='yt-project', repo='yt')
            outputs.append([data['channel'], issue.html_url])
        except pygithub3.exceptions.NotFound:
            pass


class FidoUserRepoQuery(FidoCommand):
    regex = re.compile(r'^What is (my repo).*$', re.IGNORECASE).match

    def run(self, match, data, outputs):
        dbquery = tinydb.Query()
        repo = DB.search(dbquery.user == data["user"])
        if repo:
            outputs.append([data['channel'], repo[0]["repo"]])
        else:
            outputs.append([data['channel'], "I have no clue"])


class FidoUserRepoKeep(FidoCommand):
    regex = re.compile(r'^(.*/.*) is my repo$').match

    def run(self, match, data, outputs):
        dbquery = tinydb.Query()
        if not DB.update({'repo': match[0]},
                         cond=dbquery.user == data["user"]):
            DB.insert({'user': data["user"], 'repo': match[0]})
        outputs.append([data['channel'], "Got it!"])


class FidoUserRepoForget(FidoCommand):
    regex = re.compile(r'^(forget) my repo$').match

    def run(self, match, data, outputs):
        dbquery = tinydb.Query()
        if DB.remove(dbquery.user == data["user"]):
            outputs.append([data['channel'], "Roger!"])


class FidoHelpMe(FidoCommand):
    regex = re.compile(r'^.*(fido:? help).*$', re.IGNORECASE).match

    def run(self, match, data, outputs):
        msg = ""
        for command in FIDO_COMMANDS:
            msg += "`{}`".format(command.regex.__self__.pattern)
            if command.help_msg is not None:
                msg += " " + command.help_msg
            msg += "\n"
        outputs.append([data['channel'], msg])


def _get_build_params(build):
    build_desc = '???'
    for action in build["actions"]:
        try:
            for param in action["parameters"]:
                if param["name"] == "IRKMSG":
                    build_desc = param["value"]
        except KeyError:
            pass
    return build_desc


class FidoListJenkinsJobs(FidoCommand):
    regex = re.compile(r'list job\s+(\w+)').match

    def run(self, match, data, outputs):
        job_name = match[0]
        msg = ''
        server = jenkins.Jenkins(JENKINS_URL, username=JENKINS_USER,
                                 password=JENKINS_USER_PASS)
        next_bn = server.get_job_info(job_name)['nextBuildNumber']
        last_job_id = next_bn - 1
        last_job = server.get_build_info(job_name, last_job_id)
        if last_job["building"]:
            build_desc = _get_build_params(last_job)
            msg += "Current build {} (id: {})\n".format(build_desc,
                                                        last_job['id'])

        for queued_build in server.get_queue_info():
            if queued_build["task"]["name"] == job_name:
                build_desc = _get_build_params(queued_build)
                msg += "Queued build {} (id: {})\n".format(build_desc,
                                                           queued_build['id'])
        outputs.append([data['channel'], msg])


class FidoCancelJenkinsBuild(FidoCommand):
    regex = re.compile(r'cancel build\s+(\w+)\s+(\d+)').match

    def run(self, match, data, outputs):
        server = jenkins.Jenkins(JENKINS_URL, username=JENKINS_USER,
                                 password=JENKINS_USER_PASS)
        server.cancel_queue(int(match[1]))
        outputs.append([data['channel'], "Canceling {} #{}".format(*match)])


class FidoAbortJenkinsBuild(FidoCommand):
    regex = re.compile(r'abort build\s+(\w+)\s+(\d+)').match

    def run(self, match, data, outputs):
        server = jenkins.Jenkins(JENKINS_URL, username=JENKINS_USER,
                                 password=JENKINS_USER_PASS)
        server.stop_build(match[0], int(match[1]))
        outputs.append([data['channel'], "Aborting {} #{}".format(*match)])


FIDO_COMMANDS = [
    FidoGetPRInfo(), FidoGetIssueInfo(), FidoTestPR(),
    FidoBuildDocs(), FidoUserRepoQuery(), FidoUserRepoKeep(),
    FidoUserRepoForget(), FidoHelpMe(), FidoListJenkinsJobs(),
    FidoCancelJenkinsBuild(), FidoAbortJenkinsBuild()
]
