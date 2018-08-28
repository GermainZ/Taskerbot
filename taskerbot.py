import html
import logging
import re
import sys
import time

from praw import Reddit
from praw.models.reddit.comment import Comment
from praw.models.reddit.submission import Submission
import yaml


class Bot(object):

    def __init__(self, r):
        self.r = r
        logging.info('Success.')
        self.subreddits = {}
        for subreddit in SUBREDDITS:
            logging.info('Checking subreddit: %s…', subreddit)
            self.subreddits[subreddit] = {}
            sub = self.subreddits[subreddit]
            logging.info('Loading mods…')
            sub['mods'] = list(mod.name for mod in
                               self.r.subreddit(subreddit).moderator())
            logging.info('Mods loaded: %s.', sub['mods'])
            logging.info('Loading reasons…')
            sub['reasons'] = yaml.load(html.unescape(
                self.r.subreddit(subreddit).wiki['taskerbot'].content_md))
            logging.info('Reasons loaded.')

    def refresh_sub(self, subreddit):
        logging.info('Refreshing subreddit: %s…', subreddit)
        sub = self.subreddits[subreddit]
        logging.info('Loading mods…')
        sub['mods'] = list(mod.name for mod in
                           self.r.subreddit(subreddit).moderator())
        logging.info('Mods loaded: %s.', sub['mods'])
        logging.info('Loading reasons…')
        sub['reasons'] = yaml.load(html.unescape(
            self.r.subreddit(subreddit).wiki['taskerbot'].content_md))
        logging.info('Reasons loaded.')

    def check_comments(self, subreddit):
        logging.info('Checking subreddit: %s…', subreddit)
        sub = self.subreddits[subreddit]
        for comment in self.r.subreddit(subreddit).comments(limit=100):
            if (comment.banned_by or not comment.author or
                    comment.author.name not in sub['mods']):
                continue
            report = {'source': comment, 'reason': comment.body,
                      'author': comment.author.name}
            self.handle_report(subreddit, report, comment.parent())

    def check_reports(self, subreddit):
        logging.info('Checking subreddit reports: %s…', subreddit)
        for reported_submission in self.r.subreddit(subreddit).mod.reports():
            if not reported_submission.mod_reports:
                continue

            report = {'reason': reported_submission.mod_reports[0][0],
                      'author': reported_submission.mod_reports[0][1]}
            self.handle_report(subreddit, report, reported_submission)

    def handle_report(self, subreddit, report, target):
        sub = self.subreddits[subreddit]
        # Check for @rule command.
        match = re.search(r'@rule (\w*) *(.*)', report['reason'],
                          re.IGNORECASE)
        if match:
            rule = match.group(1)
            note = match.group(2)
            logging.info('Rule %s matched.', rule)
            if rule not in sub['reasons']:
                rule = 'Generic'
            msg = sub['reasons'][rule]['Message']
            if note:
                msg = '{}\n\n{}'.format(msg, note)

            if 'source' in report:
                report['source'].mod.remove()
            target.mod.remove()

            if isinstance(target, Submission):
                logging.info('Removed submission.')
                header = sub['reasons']['Header'].format(
                    author=target.author.name)
                footer = sub['reasons']['Footer'].format(
                    author=target.author.name)
                msg = '{header}\n\n{msg}\n\n{footer}'.format(
                    header=header, msg=msg, footer=footer)
                target.reply(msg).mod.distinguish(sticky=True)
                target.mod.flair(sub['reasons'][rule]['Flair'])
                permalink = target.permalink
            elif isinstance(target, Comment):
                logging.info('Removed comment.')
                permalink = target.permalink(fast=True)

            self.log(subreddit, '{} removed {}'.format(
                report['author'], permalink))
        # Check for @spam command.
        if report['reason'].lower().startswith('@spam'):
            if 'source' in report:
                report['source'].mod.remove()
            target.mod.remove(spam=True)
            if isinstance(target, Submission):
                logging.info('Removed submission (spam).')
                permalink = target.permalink
            elif isinstance(target, Comment):
                logging.info('Removed comment (spam).')
                permalink = target.permalink(fast=True)
            self.log(subreddit, '{} removed {} (spam)'.format(
                report['author'], permalink))
        # Check for @ban command.
        temp_match = re.search(r'@ban (\d*) "([^"]*)" "([^"]*)"', report['reason'],
                          re.IGNORECASE) # Temporary ban
        perma_match = re.search(r'@ban "([^"]*)" "([^"]*)"', report['reason'],
                          re.IGNORECASE) # Permanent ban
        if (temp_match or perma_match):
            if temp_match:
                duration = match.group(1)
                reason = match.group(2)
                msg = match.group(3)
                logging.info('Ban (%s: %s -- %s) matched.', duration, reason,
                             msg)
                self.r.subreddit(subreddit).banned.add(
                    target.author.name, duration=duration, note=reason,
                    ban_message=msg)
            if perma_match:
                reason = match.group(1)
                msg = match.group(2)
                logging.info('Ban (Permanent: %s -- %s) matched.', reason,
                             msg)
                self.r.subreddit(subreddit).banned.add(
                    target.author.name, note=reason,
                    ban_message=msg)
            if 'source' in report:
                report['source'].mod.remove()
            target.mod.remove()
            logging.info('User banned.')
            self.log(subreddit, '{} banned u/{}'.format(
                report['author'], target.author.name))

    def log(self, subreddit, msg):
        logs_page = self.r.subreddit(subreddit).wiki['taskerbot_logs']
        try:
            logs_content = logs_page.content_md
        except TypeError:
            logs_content = ""
        logs_page.edit("{}{}  \n".format(logs_content, msg))

    def check_mail(self):
        logging.info('Checking mail…')
        for mail in self.r.inbox.unread():
            mail.mark_read()
            logging.info('New mail: "%s".', mail.body)
            match = re.search(r'@refresh (.*)', mail.body, re.IGNORECASE)
            if not match:
                continue
            subreddit = match.group(1)
            if subreddit in self.subreddits:
                sub = self.subreddits[subreddit]
                if mail.author in sub['mods']:
                    self.refresh_sub(subreddit)
                    mail.reply(
                        "Refreshed mods and reasons for {}!".format(subreddit))
                else:
                    mail.reply(
                        ("Unauthorized: not an r/{} mod").format(subreddit))
            else:
                mail.reply("Unrecognized sub:  {}.".format(subreddit))

    def run(self):
        while True:
            logging.info('Running cycle…')
            for subreddit in SUBREDDITS:
                try:
                    self.check_comments(subreddit)
                    self.check_reports(subreddit)
                    self.check_mail()
                except Exception as exception:
                    logging.exception(exception)
            logging.info('Sleeping…')
            time.sleep(32) # PRAW caches responses for 30s.


if __name__ == '__main__':
    with open('config.yaml') as config_file:
        CONFIG = yaml.load(config_file)
        CLIENT_ID = CONFIG['Client ID']
        CLIENT_SECRET = CONFIG['Client Secret']
        USERNAME = CONFIG['Username']
        PASSWORD = CONFIG['Password']
        SUBREDDITS = CONFIG['Subreddits']
        USER_AGENT = CONFIG['User Agent']

    logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                        format='%(asctime)s %(levelname)s: %(message)s')
    logging.info('Logging in…')
    MODBOT = Bot(Reddit(client_id=CLIENT_ID, client_secret=CLIENT_SECRET,
                        user_agent=USER_AGENT, username=USERNAME,
                        password=PASSWORD))
    MODBOT.run()
