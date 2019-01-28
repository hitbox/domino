import datetime as dt
import requests

from bs4 import BeautifulSoup as BS

class EmailError(Exception):
    pass


class DominoError(Exception):
    pass


class Email:

    def __init__(self, unid, datetime, subject, domino=None):
        self.unid = unid
        self.datetime = datetime
        self.subject = subject
        self._domino = domino
        self._body = None

    def get_body(self):
        if self._domino is None:
            raise EmailError(f"Can't download body, need {Domino!r} instance")
        return self._domino.get_body(self.unid)

    @property
    def body(self):
        if self._body is None:
            self._body = self.get_body()
        return self._body

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.unid == other.unid
        else:
            raise NotImplementedError(other.__class__.__name__)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        return f'{self.datetime!r}: {self.subject!r}'


class Domino:

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.84 Safari/537.36'}

    def __init__(self, host, username, password):
        self.session = requests.Session()
        self.host = host
        self.username = username
        self.password = password

    def get(self, *args, **kwargs):
        kwargs.setdefault('headers', self.headers)
        return self.session.get(*args, **kwargs)

    def login_url(self):
        return f'{self.host}/names.nsf?Login&username={self.username}&password={self.password}'

    def login(self, silent=False):
        url = self.login_url()
        response = self.get(url, timeout=5)
        login_success = u'You provided an invalid username or password.' not in response.text
        if silent:
            return login_success
        elif not login_success:
            raise DominoError('Username and password invalid.')

    def open_document(self, unid, view=None):
        if view is None:
            view = '$defaultview'

        url = f'{self.host}/mail/{self.username}.nsf/{view}/{unid}?OpenDocument&ui=webmail'
        return self.get(url)

    def view_entries_url(self, view=None, **options):
        if view is None:
            view = '$defaultview'

        baseurl = f'{self.host}/mail/{self.username}.nsf/{view}?ReadViewEntries'
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
        assert all(map(lambda k: isinstance(k, str), options.keys()))

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
        datestr = source['entrydata'][4]['datetime']['0'][:15]
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
