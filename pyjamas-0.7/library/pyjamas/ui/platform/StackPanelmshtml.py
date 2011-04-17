class StackPanel(ComplexPanel):

    def _setIndex(self, td, index):
        self.indices[td.uniqueID] = index

    def _getIndex(self, td):
        return self.indices.get(td.uniqueID)

