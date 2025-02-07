import traceback
import praw # simple interface to the reddit API, also handles rate limiting of requests
import time
import sqlite3

'''USER CONFIGURATION'''

APP_ID = "" 
APP_SECRET = ""
APP_URI = "https://127.0.0.1:65010/authorize_callback"
APP_SCOPES = "account creddits edit flair history identity livemanage modconfig modcontributors modflair modlog modothers modposts modself modwiki mysubreddits privatemessages read report save submit subscribe vote wikiedit wikiread"
APP_ACCOUNT_CODE = ""
APP_REFRESH = ""
# https://www.reddit.com/comments/3cm1p8/how_to_make_your_bot_use_oauth2/
USERAGENT = "Python automatic reply v0.1 - travel info for New Zealand"

NZSUBREDDIT = "newzealand" #"newzealand"
SUBREDDIT = "earthporn+worldnews+nzphotos+selftravel+backpacking+pics+environment+iwantout" #"earthporn+travel+worldnews+nzphotos"
# This is the sub or list of subs to scan for new posts. For a single sub, use "sub1". For multiple subreddits, use "sub1+sub2+sub3+..."
DO_SUBMISSIONS = True
DO_COMMENTS = True
# Look for submissions, comments, or both.
KEYWORDS = ["travel to new zealand", "travel to nz", "traveling to new zealand", "traveling to nz", "visit new zealand", "visit nz", "visiting new zealand", "visiting nz" "move to new zealand", "move to nz", "moving to new zealand", "moving to nz", "trip to new zealand", "trip to nz", "new zealand trip"]
# These are the words you are looking for
KEYAUTHORS = []
# These are the names of the authors you are looking for
# The bot will only reply to authors on this list
# Keep it empty to allow anybody.
REPLYSTRING = "[Automated response] \n\nKia Ora - interested in a holiday or moving to New Zealand? \n\nTravel: https://www.reddit.com/r/newzealand/wiki/traveladvice#wiki_as_a_tourist\n\nMoving: https://www.reddit.com/r/newzealand/wiki/traveladvice#wiki_moving_to_or_working_in_nz\n\n*This comment was generated by a bot. Beep boop.*"
# This is the word you want to put in reply
MAXPOSTS = 100
# This is how many posts you want to retrieve all at once. PRAW can download 100 at a time.
WAIT = 30
# This is how many seconds you will wait between cycles. The bot is completely inactive during this time.
CLEANCYCLES = 10
# After this many cycles, the bot will clean its database
# Keeping only the latest (2*MAXPOSTS) items

'''All done!'''

try:
    import bot
    USERAGENT = bot.aG
except ImportError:
    pass

print('Opening SQL Database.')
sql = sqlite3.connect('sql.db')
cur = sql.cursor()
cur.execute('CREATE TABLE IF NOT EXISTS oldposts(id TEXT)')

print('Logging in...')
r = praw.Reddit(USERAGENT)
r.set_oauth_app_info(APP_ID, APP_SECRET, APP_URI)
r.refresh_access_information(APP_REFRESH)
USER = r.get_redditor('nz_bot')

def replybot():
    print('Searching %s.' % SUBREDDIT)
    subreddit = r.get_subreddit(SUBREDDIT)
    nzsubreddit = r.get_subreddit(NZSUBREDDIT)
    posts = []
    if DO_SUBMISSIONS:
        posts += list(nzsubreddit.get_new(limit=MAXPOSTS))
    if DO_COMMENTS:
        posts += list(subreddit.get_comments(limit=MAXPOSTS))
    posts.reverse()

    for post in posts:
        # Anything that needs to happen every loop goes here.
        pid = post.id

        try:
            pauthor = post.author.name
        except AttributeError:
            # Author is deleted. We don't care about this post.
            continue

        if pauthor.lower() == r.user.name.lower():
            # Don't reply to yourself, robot!
            print('Will not reply to myself.')
            continue

        if KEYAUTHORS != [] and all(auth.lower() != pauthor for auth in KEYAUTHORS):
            # This post was not made by a keyauthor
            continue

        cur.execute('SELECT * FROM oldposts WHERE ID=?', [pid])
        if cur.fetchone():
            # Post is already in the database
            continue

        if isinstance(post, praw.objects.Comment):
            pbody = post.body
        else:
            pbody = '%s %s' % (post.title, post.selftext)
        pbody = pbody.lower()

        if not any(key.lower() in pbody for key in KEYWORDS):
            # Does not contain our keyword
            continue

        cur.execute('INSERT INTO oldposts VALUES(?)', [pid])
        sql.commit()
        print('Replying to %s by %s.' % (pid, pauthor))
        try:
            if isinstance(post, praw.objects.Submission):
                post.add_comment(REPLYSTRING) #submission reply
            else:
                post.reply(REPLYSTRING) #comment reply
        except praw.errors.Forbidden:
            print('403 FORBIDDEN - is the bot banned from %s?' % post.subreddit.display_name)
        except praw.errors.RateLimitExceeded:
            print('RATE LIMIT - not enough reddit karma, try again in approx 10 minutes.')


cycles = 0
while True:
    try:
        replybot()
        cycles += 1

    except Exception as e:
        traceback.print_exc()

    if cycles >= CLEANCYCLES:
        print('Cleaning database.')
        cur.execute('DELETE FROM oldposts WHERE id NOT IN (SELECT id FROM oldposts ORDER BY id DESC LIMIT ?)', [MAXPOSTS * 2])
        sql.commit()
        #cycles = 0

        print('Removing downvoted comments...')
        for comment in USER.get_comments(limit=20):
            if comment.score < 1:
                comment.delete()

        print('Exiting, will run again with cron job shortly.')
        exit()

    print('Running again in %d seconds \n' % WAIT)
    time.sleep(WAIT)
