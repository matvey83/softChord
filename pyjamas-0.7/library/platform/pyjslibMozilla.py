class List:
    def index(self, value, start=0):
        JS("""
        return this.l.indexOf(value, start);
        """)

