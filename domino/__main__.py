import argparse

from . import Domino

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('host')
    parser.add_argument('username')
    parser.add_argument('password')

    args = parser.parse_args()

    inbox = Domino(args.host, args.username, args.password)
    inbox.login()

    for i, email in enumerate(inbox.emails()):
        print
        print 'i: %s' % i
        print 'subject: %s' % email.subject
        print 'body:'
        print email.body()
        if i > 3:
            break

main()
