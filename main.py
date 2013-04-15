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

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), 'templates')
jinja_environment = \
    jinja2.Environment(loader=jinja2.FileSystemLoader(TEMPLATE_DIR))

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
        self.render_template('index.html', {})

class LoginPage(BaseHandler):

    def get(self):
        auth = tweepy.OAuthHandler(CONSUMER_TOKEN, 
        CONSUMER_SECRET, 
        CALLBACK_URL)

        try: 
            #get the request tokens
            redirect_url= auth.get_authorization_url()
            session['request_token']= (auth.request_token.key,
                auth.request_token.secret)
        except tweepy.TweepError:
            print 'Error! Failed to get request token'

        return self.redirect(redirect_url)

class Verify(BaseHandler):

    def get(self):
        verifier= self.request.get('oauth_verifier')

        auth = tweepy.OAuthHandler(CONSUMER_TOKEN, CONSUMER_SECRET)
        token = session['request_token']
        del session['request_token']

        auth.set_request_token(token[0], token[1])

        try:
                auth.get_access_token(verifier)
        except tweepy.TweepError:
                print 'Error! Failed to get access token.'

        api = tweepy.API(auth)

        auth_dict['api']=api
        auth_dict['access_token_key']=auth.access_token.key
        auth_dict['access_token_secret']=auth.access_token.secret
        return self.redirect('/analyze/')

class TwitterAnalyze(BaseHandler):

    def get(self):
        api = auth_dict['api']

        timeline = api.home_timeline(count=100)
        word_list = []
        embed = []
        text = ''

        for tweets in timeline:
            if hasattr(tweets, 'retweeted_status') and tweets.retweeted_status:
                text = tweets.retweeted_status.text
            else:
                text = tweets.text
            result = re.sub(r'(&amp;|&nbsp;|&quot;|&euro;|&lt;|&gt;)', '', text)
            result = re.sub(r'(https?)\:\/\/[A-z\-\.]+\.[A-z]{2,3}\/[A-z0-9]{2,}', '', result)
            result = re.sub(r'[^\w]', ' ', result)

            words = result.split()
            final_word = ''
            for word in words:
                if len(word) >= 3:
                    final_word = final_word + ' ' + word
            word_list.append(final_word)

        for tweets in timeline[0:10]:
            embed.append(api.get_oembed(id=tweets.id, maxwidth=500, omit_script=True))
        self.render_template('analyze.html', {'embed': embed, 'tweets': word_list})

app = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/login/', LoginPage),
    ('/verify/', Verify),
    ('/analyze/', TwitterAnalyze)
], debug=True)
