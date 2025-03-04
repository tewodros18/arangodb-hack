import sys
import os.path
from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem, QApplication, QWidget, QVBoxLayout
import ifcopenshell


class Window(QWidget):
	def __init__(self):
		QWidget.__init__(self)

		# Prepare Tree Widgets in a stretchable layout
		vbox = QVBoxLayout()
		self.setLayout(vbox)

		self.object_tree = QTreeWidget()
		vbox.addWidget(self.object_tree)
		self.object_tree.setColumnCount(3)
		self.object_tree.setHeaderLabels(["Name", "Class", "GlobalId"])

		self.twselection = self.object_tree.selectionModel()
		self.twselection.selectionChanged.connect(self.add_data)

		self.property_tree = QTreeWidget()
		vbox.addWidget(self.property_tree)
		self.property_tree.setColumnCount(3)
		self.property_tree.setHeaderLabels(["Property", "Value", "GlobalId"])

	def load_file(self, filename):
		# Import the IFC File
		self.ifc_file = ifcopenshell.open(filename)
		file_name = self.ifc_file.wrapped_data.header.file_name.name
		root_item = QTreeWidgetItem([file_name, "", ""])

		items = self.ifc_file.by_type('IfcProject')
		for item in items:
			self.add_object_in_tree(item, root_item)

		# Finish the GUI
		self.object_tree.addTopLevelItem(root_item)
		self.object_tree.expandToDepth(3)

	def add_attributes_in_tree(self, ifc_object, parent_item):
		# the individual attributes
		for att_idx in range(0, len(ifc_object)):
			# https://github.com/jakob-beetz/IfcOpenShellScriptingTutorial/wiki/02:-Inspecting-IFC-instance-objects
			att_name = ifc_object.attribute_name(att_idx)
			try:
				att_value = str(ifc_object.wrap_value(ifc_object.wrapped_data.get_argument(att_name)))
			except:
				att_value = ""
				pass
			attribute_item = QTreeWidgetItem([att_name, att_value, ""])
			parent_item.addChild(attribute_item)

	def add_inverseattributes_in_tree(self, ifc_object, parent_item):
		# Inverse Attributes
		attributes = ifc_object.wrapped_data.get_inverse_attribute_names()
		for att_name in attributes:
			attribute_item = QTreeWidgetItem([att_name, "", ""])
			parent_item.addChild(attribute_item)

	def add_properties_in_tree(self, property_set, parent_item):
		# the individual properties
		for prop in property_set.HasProperties:
			if prop.is_a('IfcPropertySingleValue'):
				property_item = QTreeWidgetItem(
					[prop.Name, str(prop.NominalValue.wrappedValue), str(prop.Unit)])
				parent_item.addChild(property_item)

	def add_quantities_in_tree(self, quantity_set, parent_item):
		# the individual quantities
		for quantity in quantity_set.Quantities:
			if quantity.is_a('IfcQuantityLength'):
				quantity_item = QTreeWidgetItem(
					[quantity.Name, str(quantity.LengthValue), str(quantity.Unit)])
				parent_item.addChild(quantity_item)
			elif quantity.is_a('IfcQuantityArea'):
				quantity_item = QTreeWidgetItem(
					[quantity.Name, str(quantity.AreaValue), str(quantity.Unit)])
				parent_item.addChild(quantity_item)
			elif quantity.is_a('IfcQuantityVolume'):
				quantity_item = QTreeWidgetItem(
					[quantity.Name, str(quantity.VolumeValue), str(quantity.Unit)])
				parent_item.addChild(quantity_item)
			elif quantity.is_a('IfcQuantityCount'):
				quantity_item = QTreeWidgetItem(
					[quantity.Name, str(quantity.CountValue), str(quantity.Unit)])
				parent_item.addChild(quantity_item)
			else:
				quantity_item = QTreeWidgetItem(
					[quantity.Name, "", str(quantity.Unit)])
				parent_item.addChild(quantity_item)

	def add_data(self):
		self.property_tree.clear()
		items = self.object_tree.selectedItems()
		for item in items:
			# the GUID is in the third column
			buffer = item.text(2)
			if not buffer:
				break
			# find the related object in our IFC file
			ifc_object = self.ifc_file.by_guid(buffer)
			if ifc_object is None:
				break
			# add items into the second tree

			# Attributes
			attributes_item = QTreeWidgetItem(["Attributes", "", buffer])
			self.property_tree.addTopLevelItem(attributes_item)
			self.add_attributes_in_tree(ifc_object, attributes_item)

			# Properties
			for definition in ifc_object.IsDefinedBy:
				if definition.is_a('IfcRelDefinesByType'):
					type_object = definition.RelatingType
					type_item = QTreeWidgetItem([type_object.Name, type_object.is_a(), type_object.GlobalId])
					self.property_tree.addTopLevelItem(type_item)
				if definition.is_a('IfcRelDefinesByProperties'):
					property_set = definition.RelatingPropertyDefinition
					# the individual properties/quantities
					if property_set.is_a('IfcPropertySet'):
						properties_item = QTreeWidgetItem([property_set.Name, property_set.is_a(), property_set.GlobalId])
						self.property_tree.addTopLevelItem(properties_item)
						self.add_properties_in_tree(property_set, properties_item)
					elif property_set.is_a('IfcElementQuantity'):
						quantities_item = QTreeWidgetItem([property_set.Name, property_set.is_a(), property_set.GlobalId])
						self.property_tree.addTopLevelItem(quantities_item)
						self.add_quantities_in_tree(property_set, quantities_item)

			self.property_tree.expandAll()

	def add_object_in_tree(self, ifc_object, parent_item):
		tree_item = QTreeWidgetItem([ifc_object.Name, ifc_object.is_a(), ifc_object.GlobalId])
		parent_item.addChild(tree_item)

		# only spatial elements can contain building elements
		if ifc_object.is_a("IfcSpatialStructureElement"):
			# using IfcRelContainedInSpatialElement to get contained elements
			for rel in ifc_object.ContainsElements:
				related_elements = rel.RelatedElements
				for element in related_elements:
					self.add_object_in_tree(element, tree_item)
		# using IfcRelAggregates to get spatial decomposition of spatial structure elements
		if ifc_object.is_a("IfcObjectDefinition"):
			for rel in ifc_object.IsDecomposedBy:
				related_objects = rel.RelatedObjects
				for related_object in related_objects:
					self.add_object_in_tree(related_object, tree_item)


if __name__ == '__main__':
	app = 0
	if QApplication.instance():
		app = QApplication.instance()
	else:
		app = QApplication(sys.argv)

	w = Window()
	w.resize(600, 800)
	filename = 'Ifc4_SampleHouse.ifc'
	if os.path.isfile(filename):
		w.load_file(filename)
		w.show()
	sys.exit(app.exec_())