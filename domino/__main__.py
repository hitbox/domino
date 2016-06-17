import argparse
import pickle

from . import Domino

def load_bodies(emails):
    # access the body attribute to make emails load their body
    for email in emails:
        print 'loading body: %s' % email
        email.body

def main():
    """
    Dump emails
    """
    parser = argparse.ArgumentParser(main.__doc__)
    parser.add_argument('host')
    parser.add_argument('username')
    parser.add_argument('password')

    parser.add_argument('-n', '--max', metavar='NUM', default=10, help='Get NUM emails from inbox.')
    parser.add_argument('-P', '--pickle', metavar='FILE', help='dump emails to pickle FILE.')

    args = parser.parse_args()

    inbox = Domino(args.host, args.username, args.password)
    inbox.login()

    emailsgenerator = inbox.emails(count=args.max)

    if args.pickle:
        with open(args.pickle, 'wb') as outputfile:
            emails = list(emailsgenerator)
            load_bodies(emails)
            pickle.dump(emails, outputfile)
    else:
        for email in emailsgenerator:
            print email

main()
