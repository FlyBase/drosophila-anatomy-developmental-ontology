import re
from alphabet_conversion import replace_greek


class Term:
    """For storing term label, synonyms and symbol.
    Ontology is an OAK Basic Ontology Interface.
    Assumes that symbols should contain greek characters where possible."""
    def __init__(self, ontology = "", id = "", symbol = "", reference = ""):
        self.ontology = ontology
        self.id = id
        self.symbol = symbol
        self.reference = reference
        self.label = ""
        self.synonyms = []
        self.add_as_synonym_gr = False
        self.add_as_synonym_en = False

    def get_synonym_info(self):
        """Finds label and synonyms for a Term in ontology."""
        self.label = self.ontology.label(self.id)
        self.synonyms = self.ontology.entity_aliases(self.id)

    def check_existing_info(self):
        """Check whether symbol is present in synonyms."""
        if self.symbol not in self.synonyms:
            self.add_as_synonym_gr = True

        if (replace_greek(self.symbol) not in self.synonyms)\
                and (self.symbol != replace_greek(self.symbol)):
            self.add_as_synonym_en = True
