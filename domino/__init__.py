import hashlib
import datetime as dt
import requests

from bs4 import BeautifulSoup as BS

class Email(object):

    def __init__(self, unid, datetime, subject, domino=None):
        self.unid = unid
        self.datetime = datetime
        self.subject = subject
        self._domino = domino
        self._body = None

    def get_body(self):
        if self._domino is None:
            raise RuntimeError("Can't download body, need %r instance" % Domino)
        return self._domino.get_body(self.unid)

    @property
    def body(self):
        if self._body is None:
            self._body = self.get_body()
        return self._body

    def __hash__(self):
        # hash string into integer
        # http://stackoverflow.com/questions/1779879/convert-32-char-md5-string-to-integer/1779913#1779913
        return int(hashlib.md5(self.unid).hexdigest(), 16)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.unid == other.unid
        else:
            raise NotImplementedError(other.__class__.__name__)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        return '%s: %s' % (self.datetime, self.subject)


# no idea if this works for all servers

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
        return self.get(url)

    def view_entries_url(self, view=None, **options):
        if view is None:
            view = '$defaultview'

        baseurl = '%s/mail/%s.nsf/%s?ReadViewEntries' % (self.host, self.username, view)
        return '&'.join((baseurl, ) + tuple('%s=%s' % (k, v) for k,v in options.items()))

    def view_entries(self, view=None, **options):
        """
        Get result of ReadViewEntries. Setting OutputFormat in options is
        ignored and JSON is always used.

        key/values of options are case insensitive and values are converted to strings.

        options defaults:
        ResortAscending = '4' (the datetime)
        Count = '25' (download at most 25 entries)

        see: http://www.ibm.com/developerworks/lotus/library/ls-Domino_URL_cheat_sheet/

        :param view: no idea what this does, $default seems to work well.
        :param options: optional arguments for ReadViewEntries, see link above.
        """
        assert all(map(lambda k: isinstance(k, basestring), options.keys()))

        options = { k.lower(): str(v).lower() for k,v in options.items() }

        options['outputformat'] = 'json'
        options.setdefault('resortascending', '4') # datetime
        options.setdefault('count', '25')

        #TODO: smaller count with restart (Start option) and continue

        url = self.view_entries_url(view=view, **options)
        response = self.get(url)

        return response.json()

    def get_body(self, unid, view=None):
        response = self.open_document(unid, view=view)
        soup = BS(response.text, 'html.parser')
        pre = soup.find('pre')
        if pre is None:
            return ''
        return pre.string.strip()

    def marshal_view_entry(self, source):
        unid = source['@unid']

        datefmt = '%Y%m%dT%H%M%S'
        datestr = source['entrydata'][4]['datetime']['0'][:len(datefmt)]
        datetime = dt.datetime.strptime(datestr, datefmt)

        subject = source['entrydata'][3]['text']['0']
        email = Email(unid, datetime, subject, domino=self)
        return email

    def marshal_view_entries(self, sequence):
        for viewentry in sequence:
            yield self.marshal_view_entry(viewentry)

    def emails(self, **options):
        """
        Generator to yield emails (unid, datetime, subject, body)
        """
        jsondata = self.view_entries(**options)

        # this list of dicts of view entries is under key 'viewentry'
        marshalgenerator = self.marshal_view_entries(jsondata['viewentry'])

        for view_entry in marshalgenerator:
            yield view_entry
