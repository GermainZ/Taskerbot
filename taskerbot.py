import html
import logging
import re
import sys
import time

from praw import Reddit
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

            # Check for @rule command.
            match = re.search(r'@rule (\w*) *(.*)', comment.body,
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

                parent = comment.parent()
                comment.mod.remove()
                parent.mod.remove()

                if parent.fullname.startswith('t3_'):
                    logging.info('Removed submission.')
                    header = sub['reasons']['Header'].format(
                        author=parent.author.name)
                    footer = sub['reasons']['Footer'].format(
                        author=parent.author.name)
                    msg = '{header}\n\n{msg}\n\n{footer}'.format(
                        header=header, msg=msg, footer=footer)
                    parent.reply(msg).mod.distinguish(sticky=True)
                    parent.mod.flair(sub['reasons'][rule]['Flair'])
                elif parent.fullname.startswith('t1_'):
                    logging.info('Removed comment.')

                self.log(subreddit, '{} removed {}'.format(
                    comment.author.name, comment.permalink(fast=True)))
            # Check for @spam command.
            if comment.body.lower().startswith('@spam'):
                parent = comment.parent()
                comment.mod.remove()
                parent.mod.remove(spam=True)
                if parent.fullname.startswith('t3_'):
                    logging.info('Removed submission (spam).')
                elif parent.fullname.startswith('t1_'):
                    logging.info('Removed comment (spam).')
                self.log(subreddit, '{} removed {} (spam)'.format(
                    comment.author.name, comment.permalink(fast=True)))
            # Check for @ban command.
            match = re.search(r'@ban (\d*) "([^"]*)" "([^"]*)"', comment.body,
                              re.IGNORECASE)
            if match:
                duration = match.group(1)
                reason = match.group(2)
                msg = match.group(3)
                logging.info('Ban (%s: %s -- %s) matched.', duration, reason,
                             msg)
                parent = comment.parent()
                comment.mod.remove()
                parent.mod.remove()
                self.r.subreddit(subreddit).banned.add(
                    parent.author.name, duration=duration, note=reason,
                    ban_message=msg)
                logging.info('User banned.')
                self.log(subreddit, '{} banned u/{}'.format(
                    comment.author.name, parent.author.name))

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
