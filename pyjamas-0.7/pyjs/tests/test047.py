global x
x = 5
x += 1

while x > 0:
    print x
    x -= 1

try:
    print 5
except:
    print 2

if __name__ == '__main__':
    print x

print 5

for x in range(10):
    print x
