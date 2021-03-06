# -*- coding: utf-8 -*-
"""
/***************************************************************************
 FmeLauncher
                                 A QGIS plugin
 Basic plugin to launch fme script from QGIS
                              -------------------
        begin                : 2017-07-18
        git sha              : $Format:%H$
        copyright            : (C) 2017 by SITN/OM
        email                : olivier.monod@ne.ch
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
import os
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from PyQt4.QtCore import QObject, SIGNAL
from PyQt4.QtGui import QAction, QIcon, QListWidgetItem
from qgis.gui import QgsMessageBar
from qgis.core import QgsVectorLayer, QgsMapLayerRegistry
# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from fme_launcher_dialog import FmeLauncherDialog
import os.path
import yaml
import subprocess


class FmeLauncher:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        self.messageBar = self.iface.messageBar()
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'FmeLauncher_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&FME Launcher')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'FmeLauncher')
        self.toolbar.setObjectName(u'FmeLauncher')
        self.dlg = FmeLauncherDialog()
        self.conf = yaml.load(
            open(os.path.dirname(os.path.abspath(__file__)) +
                 "\\fme_launcher.yaml", 'r')
        )['vars']

        self.fmeExePath = self.conf['fme_path']
        if os.path.exists(self.fmeExePath):
            self.messageBar.pushMessage("Info",
                                        str("FME ok: " + self.fmeExePath),
                                        level=QgsMessageBar.INFO)
        else:
            self.messageBar.pushMessage("Erreur",
                                        str("FME introuvable: " +
                                            self.fmeExePath),
                                        level=QgsMessageBar.CRITICAL)

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('FmeLauncher', message)

    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        # Create the dialog (after translation) and keep reference
        self.dlg = FmeLauncherDialog()

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/FmeLauncher/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'FME launcher'),
            callback=self.run,
            parent=self.iface.mainWindow())

        QObject.connect(self.dlg.button_box, SIGNAL("clicked()"),
                        self.runScript)

        for script in self.conf["scripts"]:
            params = self.conf["scripts"][script]
            self.dlg.scriptList.addItem(
                QFmeListItem(
                    params["script_path"],
                    params["name"],
                    params["output_dir"]
                )
            )

    def runScript(self):
        if len(self.dlg.scriptList.selectedItems()) > 0:
            scriptPath = self.dlg.scriptList.selectedItems()[0].scriptPath
        else:
            self.messageBar.pushMessage("Erreur",
                                        unicode("Aucun script sélectionné: ",
                                                "utf-8"),
                                        level=QgsMessageBar.CRITICAL)
            return

        if scriptPath != '':
			# p = subprocess.Popen([self.fmeExePath, scriptPath, "--stdout"], shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
			err = subprocess.call([self.fmeExePath, scriptPath], stdin=None, stdout=None, stderr=None, shell=False)
			print err
			# [out, err] = p.communicate()

        if not err:
            self.messageBar.pushMessage("OK",
                                        unicode("Le script a bien fonctionné",
                                                "utf-8"),
                                        level=QgsMessageBar.INFO)

            outputDir = self.dlg.scriptList.selectedItems()[0].outputDir
            if outputDir:
                i = 0
                for f in os.listdir(outputDir):
                    extension = f[-4:]
                    if extension == '.shp':
                        out = outputDir + "/" + f
                        layer = QgsVectorLayer(out, "result_" + str(i), "ogr")
                        crs = layer.crs()
                        crs.createFromId(2056)
                        layer.setCrs(crs)
                        QgsMapLayerRegistry.instance().addMapLayer(layer)

        else:
            self.messageBar.pushMessage("Erreur",
                                        str(err),
                                        level=QgsMessageBar.CRITICAL)

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&FME Launcher'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    def run(self):
        """Run method that performs all the real work"""
        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            self.runScript()
            pass


class QFmeListItem(QListWidgetItem):

    def __init__(self, scriptPath, text, output_dir):
        self.scriptPath = scriptPath
        self.outputDir = output_dir
        super(QFmeListItem, self).__init__()
        if text is not None:
            self.setText(text)
