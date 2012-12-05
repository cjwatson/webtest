from __future__ import unicode_literals
import os.path
import struct
from tests.compat import unittest
from webtest.compat import to_bytes
from webtest.compat import binary_type
from webtest.compat import PY3
from webob import Request
import six
import webtest


def get_files_page(uploaded_files):
    file_parts = [b"""
<html>
    <head><title>display page</title></head>
    <body>
"""]
    file_parts = []
    for uploaded_file in uploaded_files:
        filename = to_bytes(uploaded_file.filename)
        value = to_bytes(uploaded_file.value, 'ascii')
        file_parts.append(b"""
        <p>You selected '""" + filename + b"""'</p>
        <p>with contents: '""" + value + b"""'</p>
""")
    file_parts.append(b"""    </body>
</html>
""")
    return b''.join(file_parts)


def single_upload_file_app(environ, start_response):
    req = Request(environ)
    status = str("200 OK")
    if req.method == "GET":
        body = b"""
<html>
    <head><title>form page</title></head>
    <body>
        <form method="POST" id="file_upload_form"
              enctype="multipart/form-data">
            <input name="file-field" type="file" />
            <input name="button" type="submit" value="single">
        </form>
    </body>
</html>
"""
    else:
        uploaded_files = req.POST.getall("file-field")
        body = get_files_page(uploaded_files)
    headers = [
        ('Content-Type', 'text/html; charset=utf-8'),
        ('Content-Length', str(len(body)))]
    start_response(status, headers)
    assert(isinstance(body, binary_type))
    return [body]


def upload_binary_app(environ, start_response):
    req = Request(environ)
    status = str("200 OK")
    if req.method == "GET":
        body = b"""
<html>
    <head><title>form page</title></head>
    <body>
        <form method="POST" id="binary_upload_form"
              enctype="multipart/form-data">
            <input name="binary-file-field" type="file" />
            <input name="button" type="submit" value="binary" />
        </form>
    </body>
</html>
"""
    else:
        uploaded_files = req.POST.getall("binary-file-field")
        data = uploaded_files[0].value
        if PY3:
            data = struct.unpack(b'255h', data[:510])
        else:
            data = struct.unpack(str('255h'), data)
        data = b','.join([to_bytes(str(i)) for i in data])
        body = b"""
<html>
    <head><title>display page</title></head>
    <body>
        """ + data + b"""
    </body>
</html>
"""
    headers = [
        ('Content-Type', 'text/html; charset=utf-8'),
        ('Content-Length', str(len(body)))]
    start_response(status, headers)
    assert(isinstance(body, binary_type))
    return [body]


def multiple_upload_file_app(environ, start_response):
    req = Request(environ)
    status = str("200 OK")
    if req.method == "GET":
        body = b"""
<html>
    <head><title>form page</title></head>
    <body>
        <form method="POST" id="file_upload_form"
              enctype="multipart/form-data">
            <input name="file-field-1" type="file" />
            <input name="file-field-2" type="file" />
            <input name="button" type="submit" value="single">
        </form>
    </body>
</html>
"""
    else:
        uploaded_file_1 = req.POST.get("file-field-1")
        uploaded_file_2 = req.POST.get("file-field-2")
        uploaded_files = [uploaded_file_1, uploaded_file_2]
        body = get_files_page(uploaded_files)
    headers = [
        ('Content-Type', 'text/html; charset=utf-8'),
        ('Content-Length', str(len(body)))]
    start_response(status, headers)
    assert(isinstance(body, binary_type))
    return [body]


class TestFileUpload(unittest.TestCase):

    def assertFile(self, name, contents, display):
        if isinstance(name, six.binary_type):
            text_name = name.decode('ascii')
        else:
            text_name = name
        self.assertIn("<p>You selected '" + text_name + "'</p>",
                      display, display)
        if isinstance(contents, six.binary_type):
            text_contents = contents.decode('ascii')
        else:
            text_contents = contents
        self.assertIn("<p>with contents: '" + text_contents + "'</p>",
                      display, display)

    def test_no_uploads_error(self):
        app = webtest.TestApp(single_upload_file_app)
        app.get('/').forms["file_upload_form"].upload_fields()

    def test_upload_without_file(self):
        app = webtest.TestApp(single_upload_file_app)
        upload_form = app.get('/').forms["file_upload_form"]
        upload_form.submit()

    def test_file_upload_with_filename_only(self):
        uploaded_file_name = os.path.join(os.path.dirname(__file__),
                                          "__init__.py")
        uploaded_file_contents = open(uploaded_file_name).read()
        if PY3:
            uploaded_file_contents = to_bytes(uploaded_file_contents)

        app = webtest.TestApp(single_upload_file_app)
        res = app.get('/')
        self.assertEqual(res.status_int, 200)
        self.assertEqual(res.headers['content-type'],
                         'text/html; charset=utf-8')
        self.assertEqual(res.content_type, 'text/html')
        self.assertEqual(res.charset, 'utf-8')

        single_form = res.forms["file_upload_form"]
        single_form.set("file-field", (uploaded_file_name,))
        display = single_form.submit("button")
        self.assertFile(uploaded_file_name, uploaded_file_contents, display)

    def test_file_upload_with_filename_and_contents(self):
        uploaded_file_name = os.path.join(os.path.dirname(__file__),
                                            "__init__.py")
        uploaded_file_contents = open(uploaded_file_name).read()
        if PY3:
            uploaded_file_contents = to_bytes(uploaded_file_contents)

        app = webtest.TestApp(single_upload_file_app)
        res = app.get('/')
        self.assertEqual(res.status_int, 200)
        self.assertEqual(res.headers['content-type'],
                         'text/html; charset=utf-8')
        self.assertEqual(res.content_type, 'text/html')

        single_form = res.forms["file_upload_form"]
        single_form.set("file-field",
                        (uploaded_file_name, uploaded_file_contents))
        display = single_form.submit("button")
        self.assertFile(uploaded_file_name, uploaded_file_contents, display)

    def test_file_upload_binary(self):
        binary_data = struct.pack(str('255h'), *range(0, 255))
        app = webtest.TestApp(upload_binary_app)
        res = app.get('/')
        single_form = res.forms["binary_upload_form"]
        single_form.set("binary-file-field", ('my_file.dat', binary_data))
        display = single_form.submit("button")
        self.assertIn(','.join([str(n) for n in range(0, 255)]), display)

    def test_multiple_file_uploads_with_filename_and_contents(self):
        uploaded_file1_name = os.path.join(os.path.dirname(__file__),
                                           "__init__.py")
        uploaded_file1_contents = open(uploaded_file1_name).read()
        if PY3:
            uploaded_file1_contents = to_bytes(uploaded_file1_contents)
        uploaded_file2_name = __file__
        uploaded_file2_contents = open(uploaded_file2_name).read()
        if PY3:
            uploaded_file2_contents = to_bytes(uploaded_file2_contents)

        app = webtest.TestApp(multiple_upload_file_app)
        res = app.get('/')
        self.assertEqual(res.status_int, 200)
        self.assertEqual(res.headers['content-type'],
                         'text/html; charset=utf-8')
        self.assertEqual(res.content_type, 'text/html')

        single_form = res.forms["file_upload_form"]
        single_form.set("file-field-1",
                        (uploaded_file1_name, uploaded_file1_contents))
        single_form.set("file-field-2",
                        (uploaded_file2_name, uploaded_file2_contents))
        display = single_form.submit("button")
        self.assertFile(uploaded_file1_name, uploaded_file1_contents, display)
        self.assertFile(uploaded_file1_name, uploaded_file1_contents, display)
