# import all 4 city functions so anyone can do:
# from cleaned_data import get_mumbai_cleaned
# or
# from cleaned_data.mumbai_cleaned import get_cleaned_data

from .mumbai_cleaned   import get_cleaned_data as get_mumbai_cleaned
from .delhi_cleaned    import get_cleaned_data as get_delhi_cleaned
from .dehradun_cleaned import get_cleaned_data as get_dehradun_cleaned
from .jodhpur_cleaned  import get_cleaned_data as get_jodhpur_cleaned
