""" Copyright 2007,2008,2009 John C. Gunther
* Copyright (C) 2009 Luke Kenneth Casson Leighton <lkcl@lkcl.net>
*
* Licensed under the Apache License, Version 2.0 (the
* "License"); you may not use this file except in compliance
* with the License. You may obtain a copy of the License at:
*
*  http:#www.apache.org/licenses/LICENSE-2.0
*
* Unless required by applicable law or agreed to in writing,
* software distributed under the License is distributed on an
* "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
* either express or implied. See the License for the specific
* language governing permissions and limitations under the
* License.
"""


"""*
*
* By implementing this interface, and passing an instance of your
* class to <tt>setCanvasFactory</tt>, you can "teach" GChart how to
* create the canvas-based widgets it needs to render non-rectangular
* aspects of your charts (solid-fill pie slices, continuously
* connected lines, solidly filled areas) much
* faster and with significantly better quality.
*
* <p>
*
* If you use <tt>GWTCanvas</tt> from the GWT incubator project for the vector
* graphics library, it's mainly a matter of adding a small chunk of
* boilerplate code (which you can find in the
* <tt>setCanvasFactory</tt> method's javadocs) to your application,
* adding <tt>gwt-incubator.jar</tt> to your build path, and
* selecting GChart's "continuously filled" option for your
* curves via <tt>getCurve().getSymbol().setFillSpacing(0)</tt>.
* See <tt>setCanvasFactory</tt> for full details.
*
* <p>
*
* @see GChart#setCanvasFactory setCanvasFactory
* @see GChartCanvasLite GChartCanvasLite
* @see GChart.Symbol#setFillSpacing setFillSpacing
* @see GChart.Symbol#setFillThickness setFillThickness
*
*"""
interface GChartCanvasFactory {
    """*
    * A method that returns a GWT <tt>Widget</tt> that implements
    * the subset of a Mozilla canvas' features that GChart
    * requires.
    * <p>
    *
    * Note that the returned object must <i>both</i> implement
    * <tt>GChartCanvasLite</tt> and be a GWT <tt>Widget</tt>.
    *
    """
    GChartCanvasLite create()



