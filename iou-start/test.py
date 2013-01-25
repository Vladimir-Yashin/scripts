#!/usr/bin/env python

class A:
    parent = None
    test = None
    val = 5

    def __getattr__(self, item):
        print("GA")
        val = self.__dict__[item]
        if val is not None:
            print("not none")
            return val
        elif self.parent is not None:
            print("parent not none")
            return getattr(self.parent, item)
        else:
            print("Nothing found")

if __name__ == "__main__":
    a = A()
    b = A()
    b.parent = a

    setattr(a, "test", 7)
    print(a.test)
    print(b.test)
