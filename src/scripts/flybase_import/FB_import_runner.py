#!/usr/bin/env python3

import sys
from FlyBase_import import FBgn_template_from_ID_list

FBgn_template_from_ID_list(ID_list=sys.argv[1], outfile=sys.argv[2])

