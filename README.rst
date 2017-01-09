Taskerbot
=========

A reddit bot to make moderation easier, especially on mobile.

Its main goal is to allow mods to remove posts while leaving removal reasons
via the bot.

Usage
=====

Taskerbot can be invoked by any comment containing one of the following
commands (**all arguments are required**):

- ``@rule {reason}``: **removes a thread, leaving an appropriate flair and
  comment**. ``reason`` is one of the removal reasons' keys (see
  `Removal reasons`_). If no corresponding removal reason is
  found, the ``Generic`` reason is used instead.

  Example: ``@rule 1``, ``@rule spam``.

- ``@ban {duration} "{reason}" "{message}"``: **bans the comment/thread's
  author**. All three arguments are required. ``duration`` is the ban's
  duration in days, ``reason`` is the ban's reason (visible only to mods), and
  ``message`` is the message the banned user will receive. ``reason`` and
  ``message`` must be between quotations (``""```) (escapes are not supported).

  Example: ``@ban 3600 "spammer" "repeatedly spamming somedomain.com"``

Multiple actions can be specified at once. Taskerbot will automatically remove
the comment that invoked it.

- **Refreshing the list of moderators/removal reasons**:

  Taskerbot loads the subreddit's list of moderators and removal reasons at
  startup. To refresh these, send Taskerbot a message containing ``@refresh
  Subreddit`` (e.g. ``@refresh Android`` to reload ``/r/Android``'s
  configuration).

  Note that this is case sensitive, so make sure it's the same as what's in the
  configuration file (see `Configuration file`_).

Only comments made by/mails sent by the subreddit's moderators are checked.

Setup
=====

Dependencies
------------

Taskerbot requires Python 3. For a list of required Python 3 libraries, see
``requirements.txt``.

The required Heroku__ files are provided with this project if you're interested
in running it on a Heroku app. For example (after setup):

.. code:: py

   heroku ps:scale bot=1 --app app-name-here

__ https://heroku.com/

Requirements
------------

``/u/Taskerbot`` doesn't accept new additions as we want to keep an acceptable
load. That being said, you're free to run your own instance.

You'll first want to create a new account and make it a mod of your subreddit.
Required permissions are: access, flair, posts, and wiki.

Configuration
-------------

Taskerbot uses `YAML`_ for its configuration files. You can find a good
document covering the syntax here__.

__ https://docs.ansible.com/ansible/YAMLSyntax.html

.. _Configuration file:

Configuration file
~~~~~~~~~~~~~~~~~~

The ``config.yaml`` file must contain the bot's username, password and a list
of subreddits to patrol. The syntax is as follows:

.. code:: yaml

   User Agent: 'user agent here'
   Client ID: 'client id here'
   Client Secret: 'client secret here'
   Username: 'bot username here'
   Password: 'bot password here'
   Subreddits:
       - 'SomeSubreddit'
       - 'AnotherSubreddit'
       - 'YetAnotherSub'

To obtain the client ID and secret, please follow reddit's `OAuth2 First Steps
guide`_.

Use a `YAML validator`_ to make sure the configuration file is valid.

.. _Removal reasons:

Removal reasons
~~~~~~~~~~~~~~~

This step must be performed for every new subreddit you want Taskerbot to
patrol.

1. Create a new wiki page on the subreddit called ``taskerbot``.
   For example, if you want Taskerbot to patrol ``/r/Android``, you must create
   ``/r/Android/wiki/taskerbot``.
2. Fill the page with the reasons you want -- ``Header``, ``Footer`` and
   ``Generic`` are required reasons so make sure you include at least those:

   .. code:: yaml

      Header: "Sorry {author}, your submission has been removed:"

      Footer: "If you would like to appeal, please message the moderators. *I am a bot, but this message was generated at the instruction of a human moderator.*"

      Generic:

          Flair: 'Removed'

          Message: |
              Please review our sidebar for the complete list of rules.

      1:

          Flair: "Removed (Rule 1)"

          Message: |
              Sorry, your post was removed as it breaks rule 1!
              Check our wiki for more info.

      2:

          Flair: "Removed (Rule 2)"

          Message: |
              Sorry, your post was removed as it breaks rule 2!
              Check our wiki for more info.

              Also consider checking some of our sister subreddits if you want to
              do XYZ:

              - /r/SomeSubreddit - for X.
              - /r/SomeOtherSubreddit - for Y.
              - /r/YetAnotherSubreddit - for Z.

      spam:

          Flair: "Removed (Spam)"

          Message: |
              Sorry, your post was removed as we don't like spam!
              Check our wiki for more info.

   **Reasons' keys cannot contain spaces** (e.g. in the example above, ``1``
   and ``spam`` are fine, but ``reason 2`` is not).

   Each custom removal reason must have two entries: ``Flair``, which will be
   what the removed thread's flair is set to, and ``Message``, which is the
   comment Taskerbot will leave in the thread.

   Also note that Taskerbot will automatically replace all instances of
   ``{author}`` in the ``Header`` and ``Footer`` with the author's username.

   You can check `/r/Android's taskerbot wiki page`__ for a real example (click
   "View source" in the bottom right).

   __ https://www.reddit.com/r/Android/wiki/taskerbot

Use a `YAML validator`_ to make sure the configuration file is valid.

.. _YAML validator: http://www.yamllint.com/
.. _YAML: http://www.yaml.org/
.. _OAuth2 First Steps guide: https://github.com/reddit/reddit/wiki/OAuth2-Quick-Start-Example#first-steps
