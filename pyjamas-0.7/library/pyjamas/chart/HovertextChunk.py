"""
* Copyright 2007,2008,2009 John C. Gunther
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
*
"""

import re

userpattern = re.compile("[a-zA-Z][a-zA-Z0-9_]*}.*")

HOVERTEXT_PARAM_NONE = 0; # plain old text
HOVERTEXT_PARAM_X = 1;  # ${x}
HOVERTEXT_PARAM_Y = 2;  # ${y}
HOVERTEXT_PARAM_PIESLICESIZE = 3; # ${pieSlicePercent}
HOVERTEXT_PARAM_USERDEFINED = 4; # ${mySpecialParameter}

# Allows hovertext templates to be parsed into "chunks"
# so that they can be expanded into hovertext faster.
class HovertextChunk:
    def __init__(self, pid, name, text):
        self.paramId = pid
        self.paramName = name
        self.chunkText = text

# returns array of "chunks" corresponding to the given
# hovertext template
def parseHovertextTemplate(htTemplate):
    if htTemplate == "":
        return []

    # takes "x=${x}; y=${y}" into {"x=", "x}; y=", "y}"}
    # Thus, except for the first, chunks contain a
    # keyword like part, followed by a string literal.
    sChunk = htTemplate.split("${")
    #HovertextChunk[] result = HovertextChunk[len(sChunk)]
    result = []

    for i in range(len(sChunk)):
        sC = sChunk[i]
        if 0 == i:
            # leading (non-parametric) plain text chunk
            result.append(HovertextChunk(HOVERTEXT_PARAM_NONE, None, sC))

        elif sC.startswith("x}"):
            result.append(HovertextChunk(
                            HOVERTEXT_PARAM_X, "x",
                            sC[len("x}"):]))

        elif sC.startswith("y}"):
            result.append(HovertextChunk(
                            HOVERTEXT_PARAM_Y, "y",
                            sC[len("y}"):]))

        elif sC.startswith("pieSliceSize}"):
            result.append(HovertextChunk(
                            HOVERTEXT_PARAM_PIESLICESIZE,
                            "pieSliceSize",
                            sC[len("pieSliceSize}"):]))

        elif userpattern.match(sC):
            # fits pattern for a user defined parameter
            closeCurlyIndex = sC.find("}")
            result.append(HovertextChunk(
                            HOVERTEXT_PARAM_USERDEFINED,
                            sC[0:closeCurlyIndex],
                            sC[closeCurlyIndex+1:]))

        else:
            # leading "${" without "paramName}". Likely a
            # typo, but output verbatim to give them a clue:
            result.append(HovertextChunk(HOVERTEXT_PARAM_NONE,
                                        None, "${" + sC))

    return result

""" hovertext associated with parsed "chunks" for a given point """
def getHovertext(htc, p):
    result = ""
    xS = None
    yS = None
    pieSlicePercentS = None
    #HoverParameterInterpreter hpi =
    hpi = p.getParent().getParent().getHoverParameterInterpreter()
    for i in range(len(htc)):
        pid = htc[i].paramId
        if pid == HOVERTEXT_PARAM_NONE:
            pass # do nothing extra

        elif  pid == HOVERTEXT_PARAM_X:
            if None == xS:
                hoverParam = None
                if None != hpi:
                    hoverParam = hpi.getHoverParameter(htc[i].paramName, p)
                if hoverParam is not None:
                    xS = hoverParam
                else:
                    axis = p.getParent().getParent().getXAxis()
                    xS = axis.formatAsTickLabel(p.getX())

            if None != xS:
                result += xS

        elif  pid == HOVERTEXT_PARAM_Y:
            if None == yS:
                hoverParam = None
                if None != hpi:
                    hoverParam = hpi.getHoverParameter(htc[i].paramName, p)
                if hoverParam is not None:
                    yS = hoverParam
                else:
                    if p.getParent().onY2():
                        axis = p.getParent().getParent().getY2Axis()
                    else:
                        axis = p.getParent().getParent().getYAxis()
                    yS = axis.formatAsTickLabel(p.getY())


            if None != yS:
                result+=yS

        elif  pid == HOVERTEXT_PARAM_PIESLICESIZE:
            if None == pieSlicePercentS:
                if None != hpi:
                    pieSlicePercentS = hpi.getHoverParameter(htc[i].paramName, p)

                else:
                    pieSliceSize = p.getParent().getSymbol().getPieSliceSize()
                    if p.getParent().onY2():
                        axis = p.getParent().getParent().getY2Axis()
                    else:
                        axis = p.getParent().getParent().getYAxis()
                    pieSlicePercentS = axis.formatAsTickLabel(100*pieSliceSize) + "%"


            result+=pieSlicePercentS

        elif  pid == HOVERTEXT_PARAM_USERDEFINED:

            if None == hpi:
                # None means "unrecognized parameter" - so
                # regenerate the original, unparsed, param spec
                # to clue them in that it was not processed.
                result += "${" + htc[i].paramName + "}"

            else:
                result += hpi.getHoverParameter(htc[i].paramName, p)

        else:
            raise IllegalStateException(
                "An illegal HOVERTEXT_PARAM_* id: " + htc[i].paramId +
                " was encountered. A GChart bug is likely to blame.")

        result+=htc[i].chunkText

    return result

"""*
* Convenience method that, given a plain text label, returns an
* HTML snippet appropriate for use as an argument to the
* <tt>setHovertextTemplate</tt> or <tt>setAnnotationText</tt>
* methods, that will display the plain text label with
* formatting appropriate for use with hovertext.
*
* @see Symbol#setHovertextTemplate setHovertextTemplate
* @see Curve.Point#setAnnotationText setAnnotationText
* @see Symbol#setHoverAnnotationSymbolType setHoverAnnotationSymbolType
*
* @param plainTextLabel the plain text label that is to be
*  HTML-wrapped to make it look like <tt>setTitle</tt>-based
*  hovertext.
*
*
"""

def formatAsHovertext(plainTextLabel):
    result = \
    "<html><div style='background-color:#FFFFF0; border-color:black; border-style:solid; border-width:1px 1px 1px 1px; padding:2px; text-align:left'>" + str(plainTextLabel) + "</div>"
    return result

