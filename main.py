#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import webapp2
import jinja2
import tweepy
import os
import re
import json

# Path to folder holding jinja2 templates
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), 'templates')
jinja_environment = \
    jinja2.Environment(loader=jinja2.FileSystemLoader(TEMPLATE_DIR))

# Twitter auth token/secret pair with callback url
CONSUMER_TOKEN='pONsbqQSKetcCXq98Utfw'
CONSUMER_SECRET='F7ZOAK3wSlPDy3AabeKSma7mjS9wfI9bSFAe690w3Q'
CALLBACK_URL = 'http://www.chen-jason.appspot.com/verify/'

session = dict()
auth_dict = dict()

class BaseHandler(webapp2.RequestHandler):

    @webapp2.cached_property
    def jinja2(self):
        return jinja2.get_jinja2(app=self.app)

    def render_template(
        self,
        filename,
        template_values,
        **template_args
        ):
        template = jinja_environment.get_template(filename)
        self.response.out.write(template.render(template_values))

class MainPage(BaseHandler):

    def get(self):
        # Renders index.html, basic home page
        self.render_template('index.html', {})

class LoginPage(BaseHandler):

    def get(self):
        # Redirects to analyze page if the session is still running (i.e. user is still
        # signed in)
        if 'api' in auth_dict:
            return self.redirect('/analyze/')

        # Creates OAuth handler for Twitter login using Tweepy
        auth = tweepy.OAuthHandler(CONSUMER_TOKEN, 
        CONSUMER_SECRET, 
        CALLBACK_URL)

        try: 
            # Get the request tokens
            redirect_url= auth.get_authorization_url()
            session['request_token']= (auth.request_token.key,
                auth.request_token.secret)
        except tweepy.TweepError:
            print 'Error! Failed to get request token'

        # Redirects to Twitter auth page
        return self.redirect(redirect_url)

class LogoutPage(BaseHandler):

    def get(self):
        # If auth token exists, clears the dictionary
        if 'api' in auth_dict:
            auth_dict.clear()

        # Redirects back to main page
        return self.redirect('/')

class Verify(BaseHandler):

    def get(self):
        verifier= self.request.get('oauth_verifier')

        # Establish connection with Twitter OAuth by passing the token/secret pair
        auth = tweepy.OAuthHandler(CONSUMER_TOKEN, CONSUMER_SECRET)

        # Error prevention in case user enters '/verify/' page without authorization
        # -> redirect to home page
        if not 'request_token' in session:
            return self.redirect('/')
        else:
            token = session['request_token']
            del session['request_token']

        auth.set_request_token(token[0], token[1])

        try:
                auth.get_access_token(verifier)
        except tweepy.TweepError:
                print 'Error! Failed to get access token.'

        api = tweepy.API(auth)

        # Error prevention in case user enters '/verify/' page without authorization
        # -> redirect to home page
        if auth.access_token is None:
            return self.redirect('/')
        else:
            # Stores the access to the api as well as the access token in the dictionary
            auth_dict['api']=api
            auth_dict['access_token_key']=auth.access_token.key
            auth_dict['access_token_secret']=auth.access_token.secret
            return self.redirect('/analyze/')

class TwitterAnalyze(BaseHandler):

    def get(self):
        # Error prevention in case user enters '/analyze/' page without authorization
        # -> redirect to home page
        if not 'api' in auth_dict:
            return self.redirect('/')
        else:
            api = auth_dict['api']

        # Retrieve latest 100 tweets from users home timeline
        timeline = api.home_timeline(count=100)
        word_list = []
        embed = []
        text = ''

        for tweets in timeline:
            # Acquires original tweet if possible
            if hasattr(tweets, 'retweeted_status') and tweets.retweeted_status:
                text = tweets.retweeted_status.text
            else:
                text = tweets.text

            # Simple regex filter to take out html escape symbols, http links, and all other
            # symbols (except underscore)
            result = re.sub(r'(&amp;|&nbsp;|&quot;|&euro;|&lt;|&gt;)', '', text)
            result = re.sub(r'(https?)\:\/\/[A-z\-\.]+\.[A-z]{2,3}\/[A-z0-9]{2,}', '', result)
            result = re.sub(r'[^\w]', ' ', result)

            words = result.split()
            final_word = ''
            for word in words:
                # (Very lame) filter to take out unnecessary word less than 3 characters long
                if len(word) >= 3:
                    final_word = final_word + ' ' + word
            word_list.append(final_word)

        # Playing around oembed - takes the latest 10 tweets and turn them into embedded html
        for tweets in timeline[0:10]:
            embed.append(api.get_oembed(id=tweets.id, maxwidth=500, omit_script=True))
        self.render_template('analyze.html', {'embed': embed, 'tweets': word_list})

app = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/login/', LoginPage),
    ('/logout/', LogoutPage),
    ('/verify/', Verify),
    ('/analyze/', TwitterAnalyze)
], debug=True)
