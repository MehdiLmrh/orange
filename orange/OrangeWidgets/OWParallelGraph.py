#
# OWParallelGraph.py
#
# the base for all parallel graphs

from OWVisGraph import *
from OWDistributions import *
from qt import *
from OWTools import *
from qwt import *
from Numeric import *
from statc import pearsonr

class OWParallelGraph(OWVisGraph):
    def __init__(self, parent = None, name = None):
        "Constructs the graph"
        OWVisGraph.__init__(self, parent, name)

        self.showDistributions = 0
        self.hidePureExamples = 1
        self.showCorrelations = 1
        self.metaid = -1
        self.toolInfo = []
        self.toolRects = []
        self.useSplines = 0
        self.lastSelectedKey = 0
        
    def setShowDistributions(self, showDistributions):
        self.showDistributions = showDistributions

    def setShowAttrValues(self, showAttrValues):
        self.showAttrValues = showAttrValues

    def setHidePureExamples(self, hide):
        self.hidePureExamples = hide

    def setShowCorrelations(self, show):
        self.showCorrelations = show

    def setData(self, data):
        OWVisGraph.setData(self, data)
        self.metaid = -1
        
    #
    # update shown data. Set labels, coloring by className ....
    #
    def updateData(self, labels, className, targetValue):
        self.removeTooltips()
        self.removeCurves()
        self.removeMarkers()

        if len(self.scaledData) == 0 or len(labels) == 0: self.updateLayout(); return

        self.setAxisScaleDraw(QwtPlot.xBottom, DiscreteAxisScaleDraw(labels))
        self.setAxisScaleDraw(QwtPlot.yLeft, HiddenScaleDraw())
        if (self.showDistributions == 1 or self.showAttrValues == 1) and self.rawdata.domain[labels[len(labels)-1]].varType == orange.VarTypes.Discrete:
            self.setAxisScale(QwtPlot.xBottom, 0, len(labels)-0.5, 1)
        else:   self.setAxisScale(QwtPlot.xBottom, 0, len(labels)-1.0, 1)

        if self.showAttrValues or self.showCorrelations:
            self.setAxisScale(QwtPlot.yLeft, -0.04, 1.04, 1)
        else:
            self.setAxisScale(QwtPlot.yLeft, 0, 1, 1)

        scaleDraw = self.axisScaleDraw(QwtPlot.yLeft)
        scaleDraw.setOptions(0) 
        scaleDraw.setTickLength(0, 0, 0)

        self.setAxisMaxMajor(QwtPlot.xBottom, len(labels)-1.0)        
        self.setAxisMaxMinor(QwtPlot.xBottom, 0)

        if className != "(One color)": classNameIndex = self.attributeNames.index(className)
        else:                          classNameIndex = -1
        length = len(labels)
        indices = []
        xs = []

        # create a table of indices that stores the sequence of variable indices
        for label in labels:
            index = self.attributeNames.index(label)
            indices.append(index)

        xs = range(length)
        dataSize = len(self.scaledData[0])        

        #############################################
        # if self.hidePureExamples == 1 we have to calculate where to stop drawing lines
        # we do this by adding a integer meta attribute, that for each example stores attribute index, where we stop drawing lines
        lastIndex = indices[length-1]
        dataStop = dataSize * [lastIndex]  # array where we store index value for each data value where to stop drawing
        
        if self.hidePureExamples == 1 and className != "(One color)" and self.rawdata.domain[className].varType == orange.VarTypes.Discrete:
            # add a meta attribute if it doesn't exist yet
            if self.metaid == -1:
                self.metaid = orange.newmetaid()
                metavar = orange.IntVariable("ItemIndex")
                self.rawdata.domain.addmeta(self.metaid, metavar)
                for i in range(dataSize): self.rawdata[i].setmeta(self.metaid, i)

            for i in range(length):
                if self.rawdata.domain[indices[i]].varType != orange.VarTypes.Discrete or labels[i] == className: continue

                attr = self.rawdata.domain[indices[i]]                
                for attrVal in attr.values:
                    tempData = self.rawdata.select({attr.name:attrVal})

                    ind = 0
                    while ind < len(tempData):
                        index = int(tempData[ind].getmeta(self.metaid))
                        if dataStop[index] == lastIndex:
                            val = tempData[ind][classNameIndex]
                            break
                        ind += 1
                        
                    # do all instances belong to the same class?
                    while ind < len(tempData):
                        index = int(tempData[ind].getmeta(self.metaid))
                        if dataStop[index] != lastIndex: ind += 1; continue
                        if val != tempData[ind][classNameIndex]: break
                        ind += 1


                    #print attr, attrVal, ind, len(tempData)
                    # if all examples belong to one class we repair the meta variable values
                    if ind >= len(tempData):
                        val = indices[i]
                        for item in tempData:
                            index = int(item.getmeta(self.metaid))
                            if dataStop[index] == lastIndex:
                                dataStop[index] = val

        # first create all curves
        if targetValue != None:
            curves = [[],[]]

        #############################################
        # draw the data
        for i in range(dataSize):
            validData = 1
            # check for missing values
            for index in indices:
                if self.scaledData[index][i] == "?": validData = 0; break;
            if not validData: continue
            
            curve = QwtPlotCurve(self)
            newColor = QColor()
            if targetValue != None:
                if self.rawdata[i][classNameIndex].value == targetValue:
                    newColor = self.colorTargetValue
                    curves[1].append(curve)
                else:
                    newColor = self.colorNonTargetValue
                    curves[0].append(curve)
            elif classNameIndex != -1:
                newColor.setHsv(self.coloringScaledData[classNameIndex][i]*360, 255, 255)
                self.insertCurve(curve)
            curve.setPen(QPen(newColor))
            ys = []
            for index in indices:
                ys.append(self.scaledData[index][i])
                if index == dataStop[i]: break
            curve.setData(xs, ys)
            if self.useSplines:
                curve.setStyle(QwtCurve.Spline)

        # now add all curves. First add the gray curves (they will be shown in the back) and then the blue (target value) curves (shown in front)
        if targetValue != None:
            for curve in curves[0]: self.insertCurve(curve)
            for curve in curves[1]: self.insertCurve(curve)


        #############################################
        # do we want to show distributions with discrete attributes
        if self.showDistributions and className != "(One color)" and className != "" and self.rawdata.domain[className].varType == orange.VarTypes.Discrete:
            self.showDistributionValues(className, targetValue, self.rawdata, indices, dataStop)
            

        curve = subBarQwtPlotCurve(self)
        newColor = QColor(0, 0, 0)
        curve.color = newColor
        curve.setBrush(QBrush(QBrush.NoBrush))
        ckey = self.insertCurve(curve)
        self.setCurveStyle(ckey, QwtCurve.UserCurve)
        self.setCurveData(ckey, [1,1], [2,2])


        #############################################
        # draw vertical lines that represent attributes
        for i in range(len(labels)):
            newCurveKey = self.insertCurve(labels[i])
            self.setCurveData(newCurveKey, [i,i], [0,1])
            pen = self.curve(newCurveKey).pen(); pen.setWidth(2); self.curve(newCurveKey).setPen(pen)
            if self.showAttrValues == 1:
                attr = self.rawdata.domain[labels[i]]
                if attr.varType == orange.VarTypes.Continuous:
                    strVal = "%.2f" % (self.attrValues[attr.name][0])
                    mkey1 = self.insertMarker(strVal)
                    self.marker(mkey1).setXValue(i)
                    self.marker(mkey1).setYValue(0.0)
                    strVal = "%.2f" % (self.attrValues[attr.name][1])
                    mkey2 = self.insertMarker(strVal)
                    self.marker(mkey2).setXValue(i)
                    self.marker(mkey2).setYValue(1.0)
                    if i == 0:
                        self.marker(mkey1).setLabelAlignment(Qt.AlignRight + Qt.AlignBottom)
                        self.marker(mkey2).setLabelAlignment(Qt.AlignRight + Qt.AlignTop)
                    elif i == len(labels)-1:
                        self.marker(mkey1).setLabelAlignment(Qt.AlignLeft + Qt.AlignBottom)
                        self.marker(mkey2).setLabelAlignment(Qt.AlignLeft + Qt.AlignTop)
                    else:
                        self.marker(mkey1).setLabelAlignment(Qt.AlignCenter + Qt.AlignBottom)
                        self.marker(mkey2).setLabelAlignment(Qt.AlignCenter + Qt.AlignTop)
                elif attr.varType == orange.VarTypes.Discrete:
                    attrVals = self.getVariableValuesSorted(self.rawdata, labels[i])
                    valsLen = len(attrVals)
                    for pos in range(len(attrVals)):
                        mkey = self.insertMarker(attrVals[pos])
                        font = self.marker(mkey).font(); font.setBold(1); self.marker(mkey).setFont(font)
                        self.marker(mkey).setXValue(i)
                        self.marker(mkey).setYValue(float(1+2*pos)/float(2*valsLen))
                        self.marker(mkey).setLabelAlignment(Qt.AlignRight + Qt.AlignHCenter)
                    
        ###################################################
        # show correlations
        if self.showCorrelations == 1:
            for j in range(length-1):
                attr1 = indices[j]
                attr2 = indices[j+1]
                if self.rawdata.domain[attr1].varType == orange.VarTypes.Discrete or self.rawdata.domain[attr2].varType == orange.VarTypes.Discrete: continue
                array1 = []; array2 = []
                # create two arrays with continuous values to compute correlation
                for index in range(len(self.rawdata)):
                    array1.append(self.rawdata[index][attr1])
                    array2.append(self.rawdata[index][attr2])
                (corr, b) = pearsonr(array1, array2)
                mkey1 = self.insertMarker("%.3f" % (corr))
                self.marker(mkey1).setXValue(j+0.5)
                self.marker(mkey1).setYValue(1.0)
                self.marker(mkey1).setLabelAlignment(Qt.AlignCenter + Qt.AlignTop)


    # ##########################################
    # SHOW DISTRIBUTION BAR GRAPH
    def showDistributionValues(self, className, targetValue, data, indices, dataStop):
        # get index of class         
        classNameIndex = self.attributeNames.index(className)

        # create color table            
        count = len(data.domain[className].values)
        if count < 1:
            count = 1.0

        colors = []
        #for i in range(count): colors.append(float(1+2*i)/float(2*count))
        for i in range(count): colors.append(float(i)/float(count))

        # we create a hash table of possible class values (happens only if we have a discrete class)
        classValueIndices = self.getVariableValueIndices(data, className)
        classValueSorted  = self.getVariableValuesSorted(data, className)

        # compute what data values are valid
        indicesLen = len(indices)
        dataValid = [1]*len(data)
        for i in range(len(data)):
            for j in range(indicesLen):
                if data[i][indices[j]].isSpecial(): dataValid[i] = 0

        self.toolInfo = []        
        for graphAttrIndex in range(len(indices)):
            index = indices[graphAttrIndex]
            if data.domain[index].varType != orange.VarTypes.Discrete: continue
            attr = data.domain[index]
            attrLen = len(attr.values)
            
            values = []
            totals = [0] * attrLen

            # we create a hash table of variable values and their indices
            variableValueIndices = self.getVariableValueIndices(data, index)
            variableValueSorted = self.getVariableValuesSorted(data, index)
            
            for i in range(count):
                values.append([0] * attrLen)

            stop = indices[:graphAttrIndex]
            for i in range(len(data)):
                if self.hidePureExamples == 1 and dataStop[i] in stop: continue
                if dataValid[i] == 0: continue
                # processing for distributions
                attrIndex = variableValueIndices[data[i][index].value]
                classIndex = classValueIndices[data[i][classNameIndex].value]
                totals[attrIndex] += 1
                values[classIndex][attrIndex] += 1

            # calculate maximum value of all values - needed for scaling
            maximum = 1
            for i in range(len(values)):
                for j in range(len(values[i])):
                    if values[i][j] > maximum: maximum = values[i][j]

            # calculate the sum of totals - needed for tooltips
            sumTotals = 0
            for val in totals: sumTotals += val

            # save info for tooltips
            for i in range(attrLen):
                list= []
                for j in range(count):
                    list.append((classValueSorted[j], values[j][i]))
                list.reverse()
                y_start = float(i+1)/float(attrLen); y_end = float(i)/float(attrLen)
                x_start = float(graphAttrIndex) - 0.45; x_end = float(graphAttrIndex) + 0.45
                item = (data.domain[index].name, variableValueSorted[i], totals[i], sumTotals, list, (x_start,x_end), (y_start, y_end))
                self.toolInfo.append(item)

            # create bar curve
            for i in range(count):
                curve = subBarQwtPlotCurve(self)
                newColor = QColor()
                if targetValue != None:
                    if classValueSorted[i] == targetValue: newColor = self.colorTargetValue
                    else: newColor = self.colorNonTargetValue
                else:
                    if count < len(self.colorHueValues): newColor.setHsv(self.colorHueValues[i]*360, 255, 255)
                    else:                                newColor.setHsv(float(i)*360/float(count), 255, 255)
                curve.color = newColor
                xData = []; yData = []
                for j in range(attrLen):
                    width = float(values[i][j]*0.5) / float(maximum)
                    interval = 1.0/float(2*attrLen)
                    yOff = float(1.0 + 2.0*j)/float(2*attrLen)
                    height = 0.7/float(count*attrLen)

                    yLowBott = yOff - float(count*height)/2.0 + i*height
                    xData.append(graphAttrIndex)
                    xData.append(graphAttrIndex + width)
                    yData.append(yLowBott)
                    yData.append(yLowBott + height)

                ckey = self.insertCurve(curve)
                self.setCurveStyle(ckey, QwtCurve.UserCurve)
                self.setCurveData(ckey, xData, yData)
        self.addTooltips()
        

    def addTooltips(self):
        for i in range(len(self.toolInfo)):
            (name, value, total, sumTotals, lista, (x_start,x_end), (y_start, y_end)) = self.toolInfo[i]
            if total == 0: continue
            tooltipText = "Attribute: <b>%s</b><br>Value: <b>%s</b><br>Total instances: <b>%i</b> (%.1f%%)<br>Class distribution:<br>" % (name, value, total, 100.0*float(total)/float(sumTotals))
            for j in range(len(lista)):
                (val, count) = lista[j]
                tooltipText += "<b>%s</b> : <b>%i</b> (%.1f%%)" % (val, count, 100.0*float(count)/float(total))
                if j != len(lista)-1 : tooltipText += "<br>"
            x_1 = self.transform(QwtPlot.xBottom, x_start)
            x_2 = self.transform(QwtPlot.xBottom, x_end)
            y_1 = self.transform(QwtPlot.yLeft, y_start)
            y_2 = self.transform(QwtPlot.yLeft, y_end)
            rect = QRect(x_1, y_1, x_2-x_1, y_2-y_1)
            self.toolRects.append(rect)            
            QToolTip.add(self, rect, tooltipText)

    def removeTooltips(self):
        for rect in self.toolRects:
            QToolTip.remove(self, rect)
        self.toolRects = []

    def updateLayout(self):
        OWVisGraph.updateLayout(self)
        self.removeTooltips()
        self.addTooltips()

    """
    def updateAxes(self):
        OWVisGraph.updateAxes()        
        self.removeTooltips()
        self.addTooltips()
    """
    def updateTooltips(self):
        self.removeTooltips()
        self.addTooltips()

    # if we zoomed, we have to update tooltips    
    def onMouseReleased(self, e):
        OWVisGraph.onMouseReleased(self, e)
        self.updateTooltips()

    def onMouseMoved(self, e):
        if self.mouseCurrentlyPressed: return
        else:
            if self.lastSelectedKey != 0:
                pen = self.curvePen(self.lastSelectedKey)
                pen.setWidth(1)
                self.setCurvePen(self.lastSelectedKey, pen)
            self.lastSelectedKey = 0
            if not self.lineTracking: return
            (key, foo1, x, y, foo2) = self.closestCurve(e.pos().x(), e.pos().y())
            if key != 0:
                pen = self.curvePen(key); pen.setWidth(3); self.setCurvePen(key, pen)
                self.lastSelectedKey = key
            OWVisGraph.onMouseMoved(self, e)
            self.replot()
    
if __name__== "__main__":
    #Draw a simple graph
    a = QApplication(sys.argv)        
    c = OWParallelGraph()
    c.setCoordinateAxes(['red','green','blue','light blue', 'dark blue', 'yellow', 'orange', 'magenta'])
        
    a.setMainWidget(c)
    c.show()
    a.exec_loop()
