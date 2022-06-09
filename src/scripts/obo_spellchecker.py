#!/usr/bin/env python
# -*- coding: utf-8 -*-
# obo-spellchecker - Spellchecker for OBO-formatted ontologies
# Copyright © 2021,2022 Damien Goutte-Gattat
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

# pypi-requirements: pronto pyspellchecker click

import sys
from subprocess import run
from re import compile

from pronto import Ontology
from spellchecker import SpellChecker
import click

prog_name = "obo-spellchecker"
prog_version = "0.1.0"
prog_notice = f"""\
{prog_name} {prog_version}
Copyright © 2021 Damien Goutte-Gattat

This program is released under the terms of the 1-clause BSD licence.
"""


def die(msg):
    print(f"{prog_name}: {msg}", file=sys.stderr)
    sys.exit(1)


class OntologyTermChecker(object):
    """Checks a single ontology term.
    
    This is the base class for implementing custom checks on ontology
    terms. Derived class should implement the :meth:`get_errors` method
    which performs the actual check.
    """

    def __init__(self, name, fields=['definition', 'comment']):
        """Creates a new instance.
        
        :param name: the name of the check, as will be displayed in the
            final report
        :param fields: the list of fields within a term the check should
            be applied to
        """

        self._name = name
        self._fields = fields
        self._pre_filters = []
        self._post_filters = []

    @property
    def name(self):
        """The name of this check.
        
        This name will be displayed in front of every violation in the
        generated report.
        """

        return self._name

    @property
    def fields(self):
        """A list of field names the check should be applied to."""

        return self._fields

    @property
    def pre_filters(self):
        """A list of input filters.
        
        Those filters are applied to each text value of a term before
        the :meth:`get_errors` method is called. They can modify the
        value as needed (e.g. to remove words or patterns that would
        yield false positives). Each filter should be a function taking
        a string as argument and returning the modified string.
        """
        return self._pre_filters

    @property
    def post_filters(self):
        """A list of output filters.
        
        Those filters are applied to the list of errors as returned by
        the :meth:`get_errors` method. They can exclude an error from
        the list (e.g. to remove a false positive). Each filter should
        be a function taking a string as argument (an error found in a
        text value) and returning True to exclude that error, or False
        to keep the error as it is.
        """

        return self._post_filters

    def check_term(self, term):
        """Checks a single ontology term.
        
        This is the main client interface. Called with an ontology term,
        it returns a dictionary whose keys are term fields (`name`,
        `definition`, `comment`, or `synonyms`) and values are lists of
        errors found in the corresponding fields.
        
        :param term: the ontology term to check
        :return: a dictionary of errors for each term field
        """

        results = {}

        for field in self.fields:
            value = getattr(term, field)
            if value is None:
                continue

            if field == 'synonyms':
                result = self.check_synonyms(value)
            else:
                result = self.check_value(value)
            if len(result) > 0:
                results[field] = result

        return results

    def check_synonyms(self, synonyms):
        """Checks all the synonyms of a term."""

        result = []
        for synonym in synonyms:
            result.extend(self.check_value(synonym.description))
        return result

    def check_value(self, value):
        """Checks a single text value.
        
        This method takes care of applying the pre- and post-filters so
        that the derived classes do not have to do it.
        """

        for f in self.pre_filters:
            value = f(value)

        result = self.get_errors(value)
        return [r for r in result if not self.apply_output_filters(r)]

    def get_errors(self, value):
        """Get all errors in the given text value.
        
        This method should return a list of errors.
        """
        pass

    def apply_output_filters(self, value):
        """Check an error against all output filters."""

        for f in self.post_filters:
            if f(value):
                return True
        return False


class FullStopChecker(OntologyTermChecker):
    """Checks that definitions and comments end with a full stop."""

    def __init__(self):
        OntologyTermChecker.__init__(self, 'missing final full stop')

    def get_errors(self, value):
        if len(value) >= 1 and value[-1] not in '.?]':
            return [value.split(' ')[-1]]
        else:
            return []


class PatternChecker(OntologyTermChecker):
    """A generic check based on a regular expression."""

    def __init__(self, name, pattern, fields=['definition', 'comment']):
        OntologyTermChecker.__init__(self, name, fields)
        self._pattern = compile(pattern)

    def get_errors(self, value):
        return [f'"{e}"' for e in self._pattern.findall(value)]


class RepeatedWordsChecker(PatternChecker):

    def __init__(self):
        PatternChecker.__init__(self, 'repeated words', '\\b(\w+)\s+\\1\\b')


class RepeatedSpacesChecker(PatternChecker):

    def __init__(self):
        PatternChecker.__init__(self, 'repeated spaces', '(\s)\\1+')

    def get_errors(self, value):
        m = self._pattern.findall(value)
        if len(m) > 0:
            return [f"{len(m)} repeated whitespace(s)"]
        else:
            return []


class RepeatedPunctuationChecker(PatternChecker):

    def __init__(self):
        PatternChecker.__init__(self, 'repeated punctuation',
                                '(?:[^.]\.\.(?:[^.]|\Z))|(?:,,)|(?:\?\?)|(?:!!)|(?:;;)')


class TermSpellChecker(OntologyTermChecker):

    def __init__(self):
        OntologyTermChecker.__init__(self, 'misspelling',
                                     fields=['name', 'definition', 'comment',
                                             'synonyms'])
        self._checker = SpellChecker()
        self._short_word_threshold = 4
        self._post_filters = [self._exclude_words_with_number,
                              self._exclude_short_word_filter]
        self._input_word_filters = [self._exclude_all_uppercase_words,
                                    self._exclude_camelcase_words]

    def add_custom_dictionary(self, dictionary):
        self._checker.word_frequency.load_text(dictionary)

    def get_errors(self, value):
        words = self._checker.split_words(value)
        words = [w for w in words if not self._apply_word_filters(w)]

        errors = self._checker.unknown(words)
        return errors

    def _apply_word_filters(self, word):
        for f in self._input_word_filters:
            if f(word):
                return True
        return False

    def _exclude_words_with_number(self, word):
        return not word.isalpha()

    def _exclude_all_uppercase_words(self, word):
        return word.isupper()

    def _exclude_camelcase_words(self, word):
        return word[0].islower() and not word[1:].islower()

    def _exclude_short_word_filter(self, word):
        return len(word) < self._short_word_threshold


def _load_dictionary(location):
    if location[0] == '|':
        r = run(location[1:], shell=True, capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"Command failed ({r.returncode})")
        return r.stdout
    else:
        with open(location, 'r') as f:
            return f.read()


@click.command(context_settings={'help_option_names': ['-h', '--help']})
@click.version_option(version=prog_version, message=prog_notice)
@click.argument('obofile')
@click.option('--output', '-o', type=click.File('w'), default=sys.stdout,
              help="""Write the report to the specified FILE instead
                      of standard output.""")
@click.option('--dictionary', '-d', multiple=True, metavar='DICT',
              help="""Use the specified additional dictionary.
                      This option may be used multiple times to use
                      as many additional dictionaries as needed.
                      If DICT starts with a pipe character ('|'),
                      it is interpreted as a command that is expected
                      to write the dictionary to its standard output. """)
@click.option('--obsolete/--no-obsolete', default=False,
              help="""Check terms marked as obsolete.""")
def check_ontology(obofile, output, dictionary, obsolete):
    """Spell-check the specified OBOFILE.
    
    This command performs a spell-check on the ontology in the
    provided OBO file. For every term defined in the ontology,
    it looks for misspelled words in the label, the definition,
    and any comment and synonym.
    
    It produces a report listing the misspelled words for each
    term.
    """

    try:
        onto = Ontology(obofile)
    except Exception as e:
        raise RuntimeError(f"Cannot load ontology: {e}")

    spell_checker = TermSpellChecker()
    for dictfile in dictionary:
        try:
            dictdata = _load_dictionary(dictfile)
        except Exception as e:
            raise RuntimeError(f"Cannot load dictionary: {e}")
        spell_checker.add_custom_dictionary(dictdata)

    checkers = [spell_checker,
                FullStopChecker(),
                RepeatedWordsChecker(),
                RepeatedSpacesChecker(),
                RepeatedPunctuationChecker()]

    for term in sorted(onto.terms()):
        if term.obsolete and not obsolete:
            continue

        term_shown = False

        for checker in checkers:
            r = checker.check_term(term)
            if len(r) == 0:
                continue

            if not term_shown:
                output.write(f"Term: {term.name} ({term.id})\n")
            for k, v in r.items():
                output.write(f"{checker.name}: in {k}: ")
                output.write(" ".join(sorted(v)))
                output.write("\n")
            output.write("\n")


if __name__ == '__main__':
    check_ontology()
