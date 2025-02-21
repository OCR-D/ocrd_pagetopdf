from __future__ import absolute_import

from importlib.metadata import version
from datetime import datetime
from typing import Dict, List, Optional
import os.path
from tempfile import TemporaryDirectory
from logging import getLogger
import subprocess
import codecs

from lxml import etree
from ocrd_models.constants import NAMESPACES as NS

def get_structure(metsroot):
    try:
        structlink = next(metsroot.iterfind('.//mets:structLink', NS))
        smlinks = {link.get('{http://www.w3.org/1999/xlink}from'):
                   link.get('{http://www.w3.org/1999/xlink}to')
                   for link in reversed(structlink.findall('./mets:smLink', NS))}
        phymap = next(structmap for structmap in metsroot.iterfind('.//mets:structMap', NS)
                      if structmap.get('TYPE') == 'PHYSICAL')
        topdiv = next(phymap.iterfind('./mets:div', NS))
        pages = {page.get('ID'): page.get('ORDER') or order
                 for order, page in enumerate(topdiv.findall('./mets:div', NS))
                 if page.get('TYPE') == "page"}
        logmap = next(structmap for structmap in metsroot.iterfind('.//mets:structMap', NS)
                      if structmap.get('TYPE') == 'LOGICAL')
        topdiv = next(logmap.iterfind('./mets:div', NS))
        # descend to deepest ADM
        while topdiv.get('ADMID') is None:
            topdiv = topdiv.find('./mets:div', NS)
        # we want to dive into multivolume_work, periodical, newspaper, year, month...
        # we are looking for issue, volume, monograph, lecture, dossier, act, judgement, study, paper, *_thesis, report, register, file, fragment, manuscript...
        innerdiv = topdiv
        while (topdiv.find('./mets:div', NS) is not None and
               topdiv.find('./mets:div', NS).get('ADMID') is not None):
            innerdiv = topdiv
            topdiv = topdiv.find('./mets:div', NS)
        #for div in innerdiv.iterdescendants('{%s}div' % NS['mets']):
        def find_depth(div, depth=0):
            return {
                'label': div.get('LABEL') or div.get('ORDERLABEL'),
                'type': div.get('TYPE'),
                'id': div.get('ID'),
                'page': pages.get(smlinks.get(div.get('ID'), ''), ''),
                'depth': depth,
                'subs': [find_depth(subdiv, depth+1) for subdiv in div.findall('./mets:div', NS)]
            }
        struct = find_depth(innerdiv)
        return struct
    except StopIteration:
        return None

def iso8601toiso32000(datestring):
    date = datetime.fromisoformat(datestring)
    offset = date.utcoffset()
    tz_hours, tz_seconds = divmod(offset.seconds if offset else 0, 3600)
    tz_minutes = tz_seconds // 60
    datestring = date.strftime("%Y%m%d%H%M%S")
    datestring += f"Z{tz_hours}'{tz_minutes}'"
    return datestring

def gettext(element):
    if element is not None:
        return element.text
    return ""

def get_metadata(mets):
    mets = mets._tree.getroot()
    metshdr = mets.find('.//mets:metsHdr', NS)
    createdate = metshdr.attrib.get('CREATEDATE', '') if metshdr is not None else ''
    modifieddate = metshdr.attrib.get('LASTMODDATE', '') if metshdr is not None else ''
    creator = mets.xpath('.//mets:agent[@ROLE="CREATOR"]/mets:name', namespaces=NS)
    creator = creator[0].text if len(creator) else ""
    mods = mets.find('.//mods:mods', NS)
    titlestring = ""
    titleinfos = mods.findall('.//mods:titleInfo', NS)
    for titleinfo in titleinfos:
        if titleinfo.getparent().tag == "{%s}relatedItem" % NS['mods']:
            continue
        titlestring += " - ".join(gettext(titlepart)
                                  for titlepart in (
                                          [titleinfo.find('.//mods:title', NS)] +
                                          titleinfo.findall('.//mods:subtitle', NS) +
                                          [titleinfo.find('.//mods:partNumber', NS)] +
                                          [titleinfo.find('.//mods:partName', NS)])
                                  if titlepart is not None)
        break
    author = (mods.xpath('.//mods:name[mods:role/text()="aut"]'
                        '/mods:namePart[@type="family" or @type="given"]', namespaces=NS) +
              mods.xpath('.//mods:name[mods:role/text()="cre"]'
                         '/mods:namePart[@type="family" or @type="given"]', namespaces=NS))
    author = next((part.text for part in author
                   if part.attrib["type"] == "given"), "") \
        + next((" " + part.text for part in author
                if part.attrib["type"] == "family"), "")
    publisher = publdate = digidate = ""
    origin = mods.find('.//mods:originInfo', NS)
    if origin is not None:
        publisher = gettext(origin.find('.//mods:publisher', NS))
        publdate = gettext(origin.find('.//mods:dateIssued', NS))
        digidate = gettext(origin.find('.//mods:dateCaptured', NS))
    keywords = publisher + " (Publisher)" if publisher else ""
    access = gettext(mods.find('.//mods:accessCondition', NS))
    return {
        'Author': author,
        'Title': titlestring,
        'Keywords': keywords,
        'Creator': creator,
        'Producer': __package__ + " v" + version(__package__),
        'Published': publdate,
        'Digitized': digidate,
        'CreationDate': iso8601toiso32000(createdate) if createdate else "",
        'ModDate': iso8601toiso32000(modifieddate) if modifieddate else "",
        # not part of DOCINFO:
        'Perms': access,
        'MODS': etree.tostring(mods, pretty_print=True, encoding="utf-8").decode("utf-8"),
        'TOC': get_structure(mets)
    }

def read_from_mets(mets, filegrp, page_ids, pagelabel='pageId'):
    file_names = []
    pagelabels = []
    file_ids = []
    if pagelabel == "pagelabel":
        pages = mets.get_physical_pages(for_pageIds=page_ids, return_divs=True)
    for f in mets.find_files(mimetype='application/pdf', fileGrp=filegrp, pageId=page_ids or None):
        # ignore existing multipage PDFs
        if f.pageId:
            file_names.append(f.local_filename)
            if pagelabel == "pagenumber":
                pass
            elif pagelabel == "pagelabel":
                for page in pages:
                    if page.get('ID') == f.pageId:
                        order = page.get('ORDER') or ''
                        orderlabel = page.get('ORDERLABEL') or ''
                        label = page.get('LABEL') or ''
                        if label and orderlabel:
                            pagelabels.append(orderlabel + ' - ' + label)
                        elif orderlabel:
                            pagelabels.append(orderlabel)
                        elif label:
                            pagelabels.append(label)
                        elif order:
                            pagelabels.append(order)
                        else:
                            pagelabels.append("")
                        break
            else:
                pagelabels.append(getattr(f, pagelabel, ""))
            file_ids.append(f.ID)
    return file_names, pagelabels, file_ids

def pdfmark_string(string):
    try:
        _ = string.encode('ascii')
        for c, escaped in [('\\', '\\\\'),
                           ('(', '\\('),
                           (')', '\\)'),
                           ('\n', '\\n'),
                           ('\t', '\\t')]:
            string = string.replace(c, escaped)
        return '({})'.format(string)
    except UnicodeEncodeError:
        bstring = codecs.BOM_UTF16_BE + string.encode('utf-16-be')
        return '<{}>'.format(''.join('{:02X}'.format(byte)
                                     for byte in bstring))

def create_pdfmarks(directory: str, pagelabels: Optional[List[str]] = None, metadata: Dict[str,str] = None) -> str:
    pdfmarks = os.path.join(directory, 'pdfmarks.ps')
    with open(pdfmarks, 'w') as marks:
        if metadata:
            mods = metadata.pop("MODS", "")
            toc = metadata.pop("TOC", None)
            marks.write("[ ")
            for metakey, metaval in metadata.items():
                if metaval:
                    marks.write(f"/{metakey} {pdfmark_string(metaval)}\n")
            marks.write("/DOCINFO pdfmark\n\n")
            if mods:
                # add XMP-embedded metadata
                # TODO (maybe): convert to other formats:
                # - DC (https://www.loc.gov/standards/mods/mods-dcsimple.html)
                # - MODS-RDF (https://www.loc.gov/standards/mods/modsrdf/primer-2.html)
                marks.write("[ /_objdef {modsMetadata}\n")
                marks.write("  /type /stream /OBJ pdfmark\n")
                marks.write("[ {modsMetadata} <<\n")
                marks.write("                 /Type /EmbeddedFile\n")
                marks.write("                 /Subtype (text/xml) cvn\n")
                marks.write("                 >> /PUT pdfmark\n")
                marks.write("[ {modsMetadata} \n\n")
                marks.write(pdfmark_string(mods))
                marks.write("\n\n /PUT pdfmark\n\n")
                marks.write("[ {modsMetadata} /CLOSE pdfmark\n")
                marks.write("[ {modsMetadata} << /Type /Metadata /Subtype /XML >> /PUT pdfmark\n")
                marks.write("[{Catalog} {modsMetadata} /Metadata pdfmark\n")
            if toc:
                def struct2bookmark(struct):
                    subs = struct['subs']
                    marks.write(f"[ /Title {pdfmark_string(struct['label'])}")
                    marks.write(f" /Page {struct['page'] or 0}")
                    if len(subs):
                        marks.write(f" /Count {len(struct['subs'])}")
                    marks.write(" /OUT pdfmark\n")
                    for sub in subs:
                        struct2bookmark(sub)
                struct2bookmark(toc)
        if pagelabels:
            marks.write("[{Catalog} <<\n\
                    /PageLabels <<\n\
                    /Nums [\n")
            for idx, pagelabel in enumerate(pagelabels):
                #marks.write(f"1 << /S /D /St 10>>\n")
                marks.write(f"{idx} << /P {pdfmark_string(pagelabel)} >>\n")
            marks.write("] >> >> /PUT pdfmark")
    return pdfmarks

def pdfmerge(inputfiles: List[str], outputfile: str, pagelabels: Optional[List[str]] = None, metadata: Dict[str,str] = None, log=None) -> None:
    if log is None:
        log = getLogger('ocrd.processor.pagetopdf')
    inputfiles = ' '.join(inputfiles)
    with TemporaryDirectory() as tmpdir:
        pdfmarks = create_pdfmarks(tmpdir, pagelabels, metadata)
        result = subprocess.run(
            "gs -q -sDEVICE=pdfwrite -dNOPAUSE -dBATCH -dSAFER "
            f"-sOutputFile={outputfile} {inputfiles} {pdfmarks}",
            shell=True, text=True, capture_output=True,
            # does not show stdout and stderr:
            #check=True,
            encoding="utf-8",
        )
        if result.stdout:
            log.debug("gs stdout: %s", result.stdout)
        if result.stderr:
            log.warning("gs stderr: %s", result.stderr)
        if result.returncode != 0:
            raise Exception("gs command for multipage PDF %s failed" % outputfile, result.args, result.stdout, result.stderr)
