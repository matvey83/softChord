

def urandom(n):
    # """urandom(n) -> str
    # Return a string of n random bytes suitable for cryptographic use.
    # """
    #try:
    #    _urandomfd = open("/dev/urandom", O_RDONLY)
    #except (OSError, IOError):
    #    raise NotImplementedError("/dev/urandom (or equivalent) not found")
    #try:
    #    bs = b""
    #    while n - len(bs) >= 1:
    #        bs += read(_urandomfd, n - len(bs))
    #finally:
    #    close(_urandomfd)
    raise NotImplementedError("/dev/urandom (or equivalent) not found")
    return bs
