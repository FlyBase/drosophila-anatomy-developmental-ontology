#!/usr/bin/env python
# -*- coding: utf-8 -*-
# fetch_flybase_authors - Get authors known to FlyBase
# Copyright © 2021 Damien Goutte-Gattat
#
# This file is part of the flybase-ontology-scripts distribution and is
# distributed under the terms of the MIT license. See the LICENSE.md
# file in the distribution for detailed conditions.

# pypi-requirements: psycopg2 click

import sys
from psycopg2 import connect
import click


def die(msg):
    print(f"fetch_flybase_authors: {msg}", file=sys.stderr)
    sys.exit(1)


@click.command(context_settings={'help_option_names': ['-h', '--help']})
@click.option('--hostname', '-H', default='chado.flybase.org', metavar='HOST',
              help="""The hostname of the database server (default:
                      chado.flybase.org).""")
@click.option('--username', '-u', default='flybase', metavar='USER',
              help="""The username to connect with (default: flybase).""")
@click.option('--database', '-d', default='flybase', metavar='NAME',
              help="""The name of the database (default: flybase).""")
@click.option('--output', '-o', type=click.File('w'), default=sys.stdout,
              help="""Write to the specified file instead of standard
                      output.""")
def fetch_flybase_authors(hostname, username, database, output):
    """Get the names of all authors known to FlyBase.
    
    This command queries FlyBase to get a sorted list of the surnames
    of all authors in the database.
    """

    try:
        conn = connect(host=hostname, user=username, dbname=database)
    except Exception as e:
        die(f"Cannot connect to the database: {e}")

    try:
        with conn.cursor() as cur:
            cur.execute('SELECT surname FROM pubauthor;')
            raw_authors = cur.fetchall()
    except Exception as e:
        die(f"Cannot query author names: {e}")
    finally:
        conn.close()

    authors = list(set([a[0] for a in raw_authors]))
    authors.sort()

    output.write('\n'.join(authors))


if __name__ == '__main__':
    fetch_flybase_authors()
