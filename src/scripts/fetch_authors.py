#!/usr/bin/env python
# -*- coding: utf-8 -*-
# fetch_flybase_authors - Get authors known to FlyBase
# Copyright © 2021 Damien Goutte-Gattat
#
# Redistribution and use of this script, with or without modifications,
# is permitted provided that the following conditions are met:
#
# 1. Redistributions of this script must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
# IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT,
# INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
# STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING
# IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

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
