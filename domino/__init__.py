import datetime as dt
import copy
import json
import requests

from pprint import pprint as pp

from bs4 import BeautifulSoup as BS

class Email(object):

    def __init__(self, domino, unid, datetime, subject):
        self.domino = domino
        self.unid = unid
        self.datetime = datetime
        self.subject = subject

    def body(self):
        return self.domino.open_document(self.unid)

class Domino(requests.Session):

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.84 Safari/537.36'}

    def __init__(self, host, username, password):
        super(Domino, self).__init__()
        self.host = host
        self.username = username
        self.password = password

    def get(self, *args, **kwargs):
        kwargs.setdefault('headers', self.headers)
        return super(Domino, self).get(*args, **kwargs)

    def login_url(self, username, password):
        return '%s/names.nsf?Login&username=%s&password=%s' % (self.host, username, password)

    def login(self, silent=False):
        response = self.get(self.login_url(self.username, self.password))
        login_success = u'You provided an invalid username or password.' not in response.text
        if silent:
            return login_success
        elif not login_success:
            raise RuntimeError('Username and password invalid.')

    def open_document(self, unid, view=None):
        if view is None:
            view = '$defaultview'

        url = '%s/mail/%s.nsf/%s/%s?OpenDocument&ui=webmail' % (self.host, self.username, view, unid)

        response = self.get(url)

        soup = BS(response.text, 'html.parser')

        pre = soup.find('pre')

        return pre.string.strip()


    def view_entries_url(self, view=None, **options):
        if view is None:
            view = '$defaultview'

        baseurl = '%s/mail/%s.nsf/%s?ReadViewEntries' % (self.host, self.username, view)
        return '&'.join((baseurl, ) + tuple('%s=%s' % (k, v) for k,v in options.items()))

    def view_entries(self, view=None, **options):
        assert all(map(lambda k: isinstance(k, basestring), options.keys()))

        options = { k.lower(): str(v).lower() for k,v in options.items() }

        options.setdefault('outputformat', 'json')
        options.setdefault('resortascending', '4') # datetime
        options.setdefault('count', '25')

        #TODO: smaller count with restart (Start option) and continue

        url = self.view_entries_url(view=view, **options)
        response = self.get(url)

        if options.get('outputformat', False):
            return response.json()

        return response

    def marshal_view_entry(self, source):
        metadata = dict(
            noteid = source['@noteid'],
            position = int(source['@position']),
            siblings = int(source['@siblings']),
            unid = source['@unid'],
        )
        emaildata = dict(
            subject = source['entrydata'][3]['text']['0'],

            # NOTE: this datetime entry has 'dst', daylight savings time
            #       theres ',00-04' crap at the end of the datetime
            datetime = dt.datetime.strptime(source['entrydata'][4]['datetime']['0'][:15], '%Y%m%dT%H%M%S')
        )
        viewentry = {'__metadata__': metadata}
        viewentry.update(**emaildata)

        # not sure if I want to throw away all that yet

        email = Email(self, viewentry['__metadata__']['unid'], viewentry['datetime'], viewentry['subject'])
        return email

    def marshal_view_entries(self, sequence):
        for viewentry in sequence:
            yield self.marshal_view_entry(viewentry)

    def emails(self, matcher=None, **options):
        jsondata = self.view_entries(**options)

        # this list of dicts of view entries is under key 'viewentry'
        view_entries = jsondata['viewentry']

        marshalgenerator = self.marshal_view_entries(view_entries)

        if matcher is None:
            for view_entry in marshalgenerator:
                yield view_entry

        for view_entry in marshalgenerator:
            if matcher(view_entry):
                yield view_entry
