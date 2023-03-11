import hashlib
import sys

print('Hashing "' + sys.argv[1] + '"')
hash = hashlib.sha512()
hash.update(sys.argv[1].encode('utf-8').strip())
password_hash = hash.hexdigest()

print(password_hash)
