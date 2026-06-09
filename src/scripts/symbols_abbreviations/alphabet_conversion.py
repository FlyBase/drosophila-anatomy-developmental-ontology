GrEn_alphabet = {
    u'\u0391': 'Alpha',
    u'\u0392': 'Beta',
    u'\u0393': 'Gamma',
    u'\u0394': 'Delta',
    u'\u03B1': 'alpha',
    u'\u03B2': 'beta',
    u'\u03B3': 'gamma',
    u'\u03B4': 'delta',
}
# truncated. original found here: https://gist.github.com/beniwohli/765262

EnGr_alphabet = {v: k for k, v in GrEn_alphabet.items()}

def replace_spelled(word):
    """Replaces spelled out greeks within a string (word) with greek symbols."""
    for key in EnGr_alphabet.keys():
        word = word.replace(key, EnGr_alphabet[key])
    return word

def replace_greek(word):
    """Replaces greek symbols within a string (word) with spelled out greeks."""
    for key in GrEn_alphabet.keys():
        word = word.replace(key, GrEn_alphabet[key])
    return word

