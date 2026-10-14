"""Banner di avvio. Modifica qui arte ASCII, tagline e colori."""
from . import __version__

# ---- PERSONALIZZA QUI ------------------------------------------------------
BANNER_ART = r"""
               . . : : .                          []                  
           . : : : : : : : : .                    []        GGGG   OOOO   DDD   /  SSS      EEEE  Y   Y  EEEE
       . : : : : . . . . : : : : .                []       G      O    O  D  D    S         E      Y Y   E
     . : : : .  . : : : .  . : : : .              []       G  GG  O    O  D   D    SSS      EEE     Y    EEE
   . : : : .  : : : o : : :  . : : : .            []       G   G  O    O  D  D        S     E       Y    E
  : : : : .  : : o o o o : :  . : : : :           []        GGGG   OOOO   DDD     SSSS      EEEE    Y    EEEE
 : : : : :   : o o @ @ o o :   : : : : :          []
< : : : :    : o @ @ @ o o :    : : : : >         []        --INTELLIGENCE | PENTESTING | SOCIAL ENGINEERING--
 : : : : :   : o o @ @ o o :   : : : : :          []
  : : : : .  : : o o o o : :  . : : : :           []    III  N   N  III  T-T-T  III     A    T-T-T  III  V   V  EEEEEE
   . : : : .  : : : o : : :  . : : : .            []     I   NN  N   I     T     I     A A     T     I   V   V  E     
     . : : : .  . : : : .  . : : : .              []     I   N N N   I     T     I    AAAAA    T     I   V   V  EEEE  
       . : : : : . . . . : : : : .                []     I   N  NN   I     T     I   A     A   T     I    V V   E     
           . : : : : : : : : .                    []    III  N   N  III    T    III  A     A   T    III    V    EEEEEE
               . : : . .                          []
"""
TAGLINE = "Web Analysis and Reconnaissance MultiTool - cross-platform"
AUTHOR = "God's Eye Initiative"
# ----------------------------------------------------------------------------

PURPLE = "\033[35m"
CYAN = "\033[96m"
DIM = "\033[2m"
RESET = "\033[0m"


def print_banner(color: bool = True) -> None:
    c = (lambda code: code) if color else (lambda code: "")
    print(f"{c(PURPLE)}{BANNER_ART}{c(RESET)}")
    print(f"  {c(CYAN)}{TAGLINE}  v{__version__}{c(RESET)}")
    print(f"  {c(DIM)}{AUTHOR}{c(RESET)}")
