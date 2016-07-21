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
        logging.debug('Logging in…')
        self.r.login(USERNAME, PASSWORD)
        logging.debug('Success.')
        self.subreddits = {}
        for subreddit in SUBREDDITS:
            logging.debug('Checking subreddit: %s…', subreddit)
            self.subreddits[subreddit] = {}
            sub = self.subreddits[subreddit]
            logging.debug('Loading mods…')
            sub['mods'] = list(redditor.name for redditor in
                               self.r.get_moderators(subreddit))
            logging.debug('Mods loaded: %s.', sub['mods'])
            logging.debug('Loading reasons…')
            sub['reasons'] = yaml.load(html.unescape(
                self.r.get_wiki_page(subreddit, 'taskerbot').content_md))
            logging.debug('Reasons loaded.')

    def refresh_sub(self, subreddit):
        logging.debug('Refreshing subreddit: %s…', subreddit)
        sub = self.subreddits[subreddit]
        logging.debug('Loading mods…')
        sub['mods'] = list(redditor.name for redditor in
                           self.r.get_moderators(subreddit))
        logging.debug('Mods loaded: %s.', sub['mods'])
        logging.debug('Loading reasons…')
        sub['reasons'] = yaml.load(html.unescape(
            self.r.get_wiki_page(subreddit, 'taskerbot').content_md))
        logging.debug('Reasons loaded.')

    def check_comments(self, subreddit):
        logging.debug('Checking subreddit: %s…', subreddit)
        sub = self.subreddits[subreddit]
        for comment in self.r.get_comments(subreddit, limit=100):
            if (comment.banned_by or not comment.author or
                    comment.author.name not in sub['mods']):
                continue

            # Check for @rule command.
            match = re.search(r'@rule (\w*)', comment.body)
            if match:
                rule = match.group(1)
                logging.debug('Rule %s matched.', rule)
                if rule not in sub['reasons']:
                    rule = 'Generic'
                msg = sub['reasons'][rule]['Message']

                parent = self.r.get_info(thing_id=comment.parent_id)
                comment.remove()
                parent.remove()

                if parent.fullname.startswith('t3_'):
                    logging.debug('Removed submission.')
                    header = sub['reasons']['Header'].format(
                        author=parent.author.name)
                    footer = sub['reasons']['Footer'].format(
                        author=parent.author.name)
                    msg = '{header}\n\n{msg}\n\n{footer}'.format(
                        header=header, msg=msg, footer=footer)
                    parent.add_comment(msg).distinguish()
                    parent.set_flair(sub['reasons'][rule]['Flair'])
                elif parent.fullname.startswith('t1_'):
                    logging.debug('Removed comment.')

            # Check for @ban command.
            match = re.search(r'@ban (\d*) "([^"]*)" "([^"]*)"', comment.body)
            if match:
                duration = match.group(1)
                reason = match.group(2)
                msg = match.group(3)
                logging.debug('Ban (%s: %s -- %s) matched.', duration, reason,
                              msg)
                parent = self.r.get_info(thing_id=comment.parent_id)
                comment.remove()
                parent.remove()
                self.r.get_subreddit(subreddit).add_ban(
                    parent.author.name, duration=duration, note=reason,
                    ban_message=msg)
                logging.debug('User banned.')

    def check_mail(self):
        logging.debug('Checking mail…')
        for mail in self.r.get_unread(True, True):
            mail.mark_as_read()
            logging.debug('New mail: "%s".', mail.body)
            match = re.search(r'@refresh (.*)', mail.body)
            if not match:
                continue
            subreddit = match.group(1)
            if subreddit in self.subreddits:
                sub = self.subreddits[subreddit]
                if mail.author.name in sub['mods']:
                    self.refresh_sub(subreddit)
                    self.r.send_message(
                        mail.author.name, "Taskerbot refresh",
                        "Refreshed mods and reasons for {}!".format(subreddit))
                else:
                    self.r.send_message(
                        mail.author.name, "Taskerbot refresh",
                        ("Unauthorized: not an r/{} mod").format(subreddit))
            else:
                self.r.send_message(mail.author.name, "Taskerbot refresh",
                                    "Unrecognized sub:  {}.".format(subreddit))

    def run(self):
        while True:
            logging.debug('Running cycle…')
            for subreddit in SUBREDDITS:
                try:
                    self.check_comments(subreddit)
                    self.check_mail()
                except Exception as exception:
                    logging.exception(exception)
            logging.debug('Sleeping…')
            time.sleep(32) # PRAW caches responses for 30s.


if __name__ == '__main__':
    with open('config.yaml') as config_file:
        CONFIG = yaml.load(config_file)
        USERNAME = CONFIG['Username']
        PASSWORD = CONFIG['Password']
        SUBREDDITS = CONFIG['Subreddits']
        USER_AGENT = CONFIG['User Agent']

    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG,
                        format='%(asctime)s %(levelname)s: %(message)s')
    logging.getLogger('requests').setLevel(logging.WARNING)
    MODBOT = Bot(Reddit(user_agent=USER_AGENT))
    MODBOT.run()
