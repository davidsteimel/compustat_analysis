import pyreadr
import pandas as pd
import numpy as np


result = pyreadr.read_r("crspdata/caz202412_r/StkMthSecurityData.rds")
df = result[None] 

