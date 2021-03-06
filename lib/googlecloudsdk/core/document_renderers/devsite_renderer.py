# Copyright 2015 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Cloud SDK markdown document HTML renderer."""

from googlecloudsdk.core.document_renderers import devsite_scripts
from googlecloudsdk.core.document_renderers import html_renderer


class DevSiteRenderer(html_renderer.HTMLRenderer):
  """Renders markdown to DevSiteHTML."""

  def __init__(self, *args, **kwargs):
    super(DevSiteRenderer, self).__init__(*args, **kwargs)

  def _Title(self):
    """Renders an HTML document title."""
    self._out.write(
        '<html devsite="">\n'
        '<head>\n')
    if self._title:
      self._out.write(
          '<title>' + self._title + '</title>\n')
    self._out.write(
        '<meta http-equiv="Content-Type" content="text/html; '
        'charset=UTF-8">\n'
        '<meta name="project_path" value="/sdk/_project.yaml">\n'
        '<meta name="book_path" value="/sdk/_book.yaml">\n')
    for comment, script in devsite_scripts.SCRIPTS:
      self._out.write('<!-- {comment} -->\n{script}\n'.format(comment=comment,
                                                              script=script))

  def _Heading(self, unused_level, heading):
    """Renders a DevSite heading.

    Args:
      unused_level: The heading level counting from 1.
      heading: The heading text.
    """
    self._heading = '</dd>\n</section>\n'
    self._out.write('\n<section id="{document_id}">\n'
                    '<dt>{heading}</dt>\n<dd class="sectionbody">\n'.format(
                        document_id=self.GetDocumentID(heading),
                        heading=heading))

  def Link(self, target, text):
    """Renders an anchor.

    Args:
      target: The link target URL.
      text: The text to be displayed instead of the link.

    Returns:
      The rendered link anchor and text.
    """
    if ('/' not in target or ':' in target or '#' in target or
        target.startswith('www.') or target.endswith('/..')):
      return '<a href="{target}">{text}</a>'.format(target=target,
                                                    text=text or target)

    # Massage the target href to match the DevSite layout.
    target_parts = target.split('/')
    if target_parts[-1] == 'help':
      target_parts.pop()
    return '<a href="/sdk/{head}/reference/{tail}">{text}</a>'.format(
        head=target_parts[0], tail='/'.join(target_parts[1:]),
        text=text or target)
