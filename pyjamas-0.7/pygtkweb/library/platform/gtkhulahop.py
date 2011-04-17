def main():
    pyjd.run()

class Scale(Range):
    def _adjustment_value_changed(self):
        value = self.adjustment.get_value()
        value = round(value, self.digits)
        self.value.setHTML(str(value))

