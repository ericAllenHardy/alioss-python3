#!/usr/bin/env python
#coding=utf-8

# Copyright (c) 2011, Alibaba Cloud Computing
# All rights reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish, dis-
# tribute, sublicense, and/or sell copies of the Software, and to permit
# persons to whom the Software is furnished to do so, subject to the fol-
# lowing conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABIL-
# ITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT
# SHALL THE AUTHOR BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

import http.client
import time
import base64
import urllib
import io
import sys
try:
    from oss.oss_util import *
except:
    from oss_util import *
try:
    from oss.oss_xml_handler import *
except:
    from oss_xml_handler import *

class OssAPI:
    '''
    A simple OSS API
    '''
    DefaultContentType = 'application/octet-stream'
    provider = PROVIDER
    __version__ = '0.3.2'
    Version = __version__
    AGENT = 'oss-python%s (%s)' % (__version__, sys.platform)

    def __init__(self, host, access_id, secret_access_key='', port=80, is_security=False):
        self.SendBufferSize = 8192
        self.RecvBufferSize = 1024*1024*10
        self.host = get_second_level_domain(host)
        self.port = port
        self.access_id = access_id
        self.secret_access_key = secret_access_key
        self.show_bar = False
        self.is_security = is_security
        self.retry_times = 5
        self.agent = self.AGENT
        self.debug = False

    def set_debug(self, is_debug):
        if is_debug:
            self.debug = True

    def set_retry_times(self, retry_times=5):
        self.retry_times = retry_times

    def set_send_buf_size(self, buf_size):
        try:
            self.SendBufferSize = (int)(buf_size)
        except ValueError:
            pass

    def set_recv_buf_size(self, buf_size):
        try:
            self.RecvBufferSize = (int)(buf_size)
        except ValueError:
            pass

    def get_connection(self, tmp_host=None):
        host = ''
        port = 80
        timeout = 10
        if not tmp_host:
            tmp_host = self.host
        host_port_list = tmp_host.split(":")
        if len(host_port_list) == 1:
            host = host_port_list[0].strip()
        elif len(host_port_list) == 2:
            host = host_port_list[0].strip()
            port = int(host_port_list[1].strip())
        if self.is_security or port == 443:
            self.is_security = True
            if sys.version_info >= (2, 6):
                return http.client.HTTPSConnection(host=host, port=port, timeout=timeout)
            else:
                return http.client.HTTPSConnection(host=host, port=port)
        else:
            if sys.version_info >= (2, 6):
                return http.client.HTTPConnection(host=host, port=port, timeout=timeout)
            else:
                return http.client.HTTPConnection(host=host, port=port)

    def sign_url_auth_with_expire_time(self, method, url, headers=None, resource="/", timeout=60, params=None):
        '''
        Create the authorization for OSS based on the input method, url, body and headers

        :type method: string
        :param method: one of PUT, GET, DELETE, HEAD

        :type url: string
        :param:HTTP address of bucket or object, eg: http://HOST/bucket/object

        :type headers: dict
        :param: HTTP header

        :type resource: string
        :param:path of bucket or object, eg: /bucket/ or /bucket/object

        :type timeout: int
        :param

        Returns:
            signature url.
        '''
        if not headers:
            headers = {}
        if not params:
            params = {}
        send_time = str(int(time.time()) + timeout)
        headers['Date'] = send_time
        auth_value = get_assign(self.secret_access_key, method, headers, resource, None, self.debug)
        params["OSSAccessKeyId"] = self.access_id
        params["Expires"] = str(send_time)
        params["Signature"] = auth_value
        sign_url = append_param(url, params)
        return sign_url

    def sign_url(self, method, bucket, object, timeout=60, headers=None, params=None):
        '''
        Create the authorization for OSS based on the input method, url, body and headers

        :type method: string
        :param method: one of PUT, GET, DELETE, HEAD

        :type bucket: string
        :param:

        :type object: string
        :param:

        :type timeout: int
        :param

        :type headers: dict
        :param: HTTP header

        :type params: dict
        :param: the parameters that put in the url address as query string

        :type resource: string
        :param:path of bucket or object, eg: /bucket/ or /bucket/object

        Returns:
            signature url.
        '''
        if not headers:
            headers = {}
        if not params:
            params = {}
        send_time = str(int(time.time()) + timeout)
        headers['Date'] = send_time
        resource = "/%s/%s%s" % (bucket, object, get_resource(params))
        auth_value = get_assign(self.secret_access_key, method, headers, resource, None, self.debug)
        params["OSSAccessKeyId"] = self.access_id
        params["Expires"] = str(send_time)
        params["Signature"] = auth_value
        url = ''
        if self.is_security:
            if is_ip(self.host):
                url = "https://%s/%s/%s" % (self.host, bucket, object)
            else:
                url = "https://%s.%s/%s" % (bucket, self.host, object)
        else:
            if is_ip(self.host):
                url = "http://%s/%s/%s" % (self.host, bucket, object)
            else:
                url = "http://%s.%s/%s" % (bucket, self.host, object)
        sign_url = append_param(url, params)
        return sign_url

    def _create_sign_for_normal_auth(self, method, headers=None, resource="/"):
        '''
        NOT public API
        Create the authorization for OSS based on header input.
        it should be put into "Authorization" parameter of header.

        :type method: string
        :param:one of PUT, GET, DELETE, HEAD

        :type headers: dict
        :param: HTTP header

        :type resource: string
        :param:path of bucket or object, eg: /bucket/ or /bucket/object

        Returns:
            signature string
        '''
        auth_value = "%s %s:%s" % (self.provider, self.access_id, get_assign(self.secret_access_key, method, headers, resource, None, self.debug))
        return auth_value

    def bucket_operation(self, method, bucket, headers=None, params=None):
        return self.http_request(method, bucket, '', headers, '', params)

    def object_operation(self, method, bucket, object, headers=None, body='', params=None):
        return self.http_request(method, bucket, object, headers, body, params)

    def http_request(self, method, bucket, object, headers=None, body='', params=None):
        '''
        Send http request of operation

        :type method: string
        :param method: one of PUT, GET, DELETE, HEAD, POST

        :type bucket: string
        :param

        :type object: string
        :param

        :type headers: dict
        :param: HTTP header

        :type body: string
        :param

        Returns:
            HTTP Response
        '''
        retry = 5
        res = None
        while retry > 0:
            retry -= 1
            tmp_bucket = bucket
            tmp_object = object
            tmp_headers = {}
            if headers and isinstance(headers, dict):
                tmp_headers = headers.copy()
            tmp_params = {}
            if params and isinstance(params, dict):
                tmp_params = params.copy()

            res = self.http_request_with_redirect(method, tmp_bucket, tmp_object, tmp_headers, body, tmp_params)
            if res.status == 301 or res.status == 302:
                self.host = helper_get_host_from_resp(res, bucket)
            else:
                return res
        return res

    def http_request_with_redirect(self, method, bucket, object, headers=None, body='', params=None):
        '''
        Send http request of operation

        :type method: string
        :param method: one of PUT, GET, DELETE, HEAD, POST

        :type bucket: string
        :param

        :type object: string
        :param

        :type headers: dict
        :param: HTTP header

        :type body: string
        :param

        Returns:
            HTTP Response
        '''
        if not params:
            params = {}
        if not headers:
            headers = {}
        if not bucket:
            resource = "/"
            headers['Host'] = self.host
        else:
            headers['Host'] = "%s.%s" % (bucket, self.host)
            resource = "/%s/" % bucket
        resource = "%s%s%s" % (resource, object, get_resource(params))
        object = urllib.parse.quote(object)
        url = "/%s" % object
        if is_ip(self.host):
            url = "/%s/%s" % (bucket, object)
            if not bucket:
                url = "/%s" % object
            headers['Host'] = self.host
        url = append_param(url, params)
        date = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime())
        headers['Date'] = date
        headers['Authorization'] = self._create_sign_for_normal_auth(method, headers, resource)
        headers['User-Agent'] = self.agent
        if check_bucket_valid(bucket) and not is_ip(self.host):
            conn = self.get_connection(headers['Host'])
        else:
            conn = self.get_connection()
        conn.request(method, url, body, headers)
        return conn.getresponse()

    def get_service(self, headers=None):
        '''
        List all buckets of user
        '''
        return self.list_all_my_buckets(headers)

    def list_all_my_buckets(self, headers=None):
        '''
        List all buckets of user
        type headers: dict
        :param

        Returns:
            HTTP Response
        '''
        method = 'GET'
        bucket = ''
        object = ''
        body = ''
        params = {}
        return self.http_request(method, bucket, object, headers, body, params)

    def get_bucket_acl(self, bucket):
        '''
        Get Access Control Level of bucket

        :type bucket: string
        :param

        Returns:
            HTTP Response
        '''
        method = 'GET'
        object = ''
        headers = {}
        body = ''
        params = {}
        params['acl'] = ''
        return self.http_request(method, bucket, object, headers, body, params)

    def get_bucket_location(self, bucket):
        '''
        Get Location of bucket
        '''
        method = 'GET'
        object = ''
        headers = {}
        body = ''
        params = {}
        params['location'] = ''
        return self.http_request(method, bucket, object, headers, body, params)

    def get_bucket(self, bucket, prefix='', marker='', delimiter='', maxkeys='', headers=None):
        '''
        List object that in bucket
        '''
        return self.list_bucket(bucket, prefix, marker, delimiter, maxkeys, headers)

    def list_bucket(self, bucket, prefix='', marker='', delimiter='', maxkeys='', headers=None):
        '''
        List object that in bucket

        :type bucket: string
        :param

        :type prefix: string
        :param

        :type marker: string
        :param

        :type delimiter: string
        :param

        :type maxkeys: string
        :param

        :type headers: dict
        :param: HTTP header

        Returns:
            HTTP Response
        '''
        method = 'GET'
        object = ''
        body = ''
        params = {}
        params['prefix'] = prefix
        params['marker'] = marker
        params['delimiter'] = delimiter
        params['max-keys'] = maxkeys
        return self.http_request(method, bucket, object, headers, body, params)

    def create_bucket(self, bucket, acl='', headers=None):
        '''
        Create bucket
        '''
        return self.put_bucket(bucket, acl, headers)

    def put_bucket(self, bucket, acl='', headers=None):
        '''
        Create bucket

        :type bucket: string
        :param

        :type acl: string
        :param: one of private public-read public-read-write

        :type headers: dict
        :param: HTTP header

        Returns:
            HTTP Response
        '''
        if not headers:
            headers = {}
        if acl != '':
            if "AWS" == self.provider:
                headers['x-amz-acl'] = acl
            else:
                headers['x-oss-acl'] = acl
        method = 'PUT'
        object = ''
        body = ''
        params = {}
        return self.http_request(method, bucket, object, headers, body, params)

    def put_bucket_with_location(self, bucket, acl='', location='', headers=None):
        '''
        Create bucket

        :type bucket: string
        :param

        :type acl: string
        :param: one of private public-read public-read-write

        :type location: string
        :param:

        :type headers: dict
        :param: HTTP header

        Returns:
            HTTP Response
        '''
        if not headers:
            headers = {}
        if acl != '':
            if "AWS" == self.provider:
                headers['x-amz-acl'] = acl
            else:
                headers['x-oss-acl'] = acl
        params = {}
        body = ''
        if location != '':
            body = r'<CreateBucketConfiguration>'
            body += r'<LocationConstraint>'
            body += location
            body += r'</LocationConstraint>'
            body += r'</CreateBucketConfiguration>'
        method = 'PUT'
        object = ''
        return self.http_request(method, bucket, object, headers, body, params)

    def delete_bucket(self, bucket, headers=None):
        '''
        Delete bucket

        :type bucket: string
        :param

        Returns:
            HTTP Response
        '''
        method = 'DELETE'
        object = ''
        body = ''
        params = {}
        return self.http_request(method, bucket, object, headers, body, params)

    def put_object_with_data(self, bucket, object, input_content, content_type=DefaultContentType, headers=None, params=None):
        '''
        Put object into bucket, the content of object is from input_content
        '''
        return self.put_object_from_string(bucket, object, input_content, content_type, headers, params)

    def put_object_from_string(self, bucket, object, input_content, content_type=DefaultContentType, headers=None, params=None):
        '''
        Put object into bucket, the content of object is from input_content

        :type bucket: string
        :param

        :type object: string
        :param

        :type input_content: string
        :param

        :type content_type: string
        :param: the object content type that supported by HTTP

        :type headers: dict
        :param: HTTP header

        Returns:
            HTTP Response
        '''
        if not headers:
            headers = {}
        headers['Content-Type'] = content_type
        headers['Content-Length'] = str(len(input_content))
        fp = io.StringIO(input_content)
        res = self.put_object_from_fp(bucket, object, fp, content_type, headers, params)
        fp.close()
        return res

    def put_object_from_bytes(self, bucket, object, input_content,
                              content_type=DefaultContentType, headers=None,
                              params=None):
        '''
        Put object into bucket, the content of object is from input_content

        :type bucket: string
        :param

        :type object: string
        :param

        :type input_content: bytes
        :param

        :type content_type: string
        :param: the object content type that supported by HTTP

        :type headers: dict
        :param: HTTP header

        Returns:
            HTTP Response
        '''
        if not headers:
            headers = {}
        headers['Content-Type'] = content_type
        headers['Content-Length'] = str(len(input_content))
        fp = io.BytesIO(input_content)
        res = self.put_object_from_fp(bucket, object, fp, content_type, headers, params)
        fp.close()
        return res

    def _open_conn_to_put_object(self, bucket, object, filesize, content_type=DefaultContentType, headers=None, params=None):
        '''
        NOT public API
        Open a connectioon to put object

        :type bucket: string
        :param

        :type filesize: int
        :param

        :type object: string
        :param

        :type input_content: string
        :param

        :type content_type: string
        :param: the object content type that supported by HTTP

        :type headers: dict
        :param: HTTP header

        Returns:
            Initialized HTTPConnection
        '''
        if not params:
            params = {}
        if not headers:
            headers = {}
        method = 'PUT'
        resource = "/%s/" % bucket
        if not bucket:
            resource = "/"
        resource = "%s%s%s" % (resource, object, get_resource(params))

        object = urllib.parse.quote(object)
        url = "/%s" % object
        if bucket:
            headers['Host'] = "%s.%s" % (bucket, self.host)
        else:
            headers['Host'] = self.host
        if is_ip(self.host):
            url = "/%s/%s" % (bucket, object)
            headers['Host'] = self.host
        url = append_param(url, params)
        date = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime())

        if check_bucket_valid(bucket) and not is_ip(self.host):
            conn = self.get_connection(headers['Host'])
        else:
            conn = self.get_connection()
        conn.putrequest(method, url)
        headers["Content-Type"] = content_type
        headers["Content-Length"] = filesize
        headers["Date"] = date
        headers["Expect"] = "100-Continue"
        headers['User-Agent'] = self.agent
        for k in headers.keys():
            conn.putheader(str(k), str(headers[k]))
        if '' != self.secret_access_key and '' != self.access_id:
            auth = self._create_sign_for_normal_auth(method, headers, resource)
            conn.putheader("Authorization", auth)
        conn.endheaders()
        return conn

    def put_object_from_file(self, bucket, object, filename, content_type='', headers=None, params=None):
        '''
        put object into bucket, the content of object is read from file

        :type bucket: string
        :param

        :type object: string
        :param

        :type fllename: string
        :param: the name of the read file

        :type content_type: string
        :param: the object content type that supported by HTTP

        :type headers: dict
        :param: HTTP header

        Returns:
            HTTP Response
        '''
        fp = open(filename, 'rb')
        if not content_type:
            content_type = get_content_type_by_filename(filename)
        res = self.put_object_from_fp(bucket, object, fp, content_type, headers, params)
        fp.close()
        return res

    def view_bar(self, num=1, sum=100):
        rate = float(num) / float(sum)
        rate_num = int(rate * 100)
        print('\r%d%% ' % (rate_num),end='')
        sys.stdout.flush()

    def put_object_from_fp(self, bucket, object, fp, content_type=DefaultContentType, headers=None, params=None):
        '''
        Put object into bucket, the content of object is read from file pointer

        :type bucket: string
        :param

        :type object: string
        :param

        :type fp: file
        :param: the pointer of the read file

        :type content_type: string
        :param: the object content type that supported by HTTP

        :type headers: dict
        :param: HTTP header

        Returns:
            HTTP Response
        '''
        tmp_object = object
        tmp_headers = {}
        tmp_params = {}
        if headers and isinstance(headers, dict):
            tmp_headers = headers.copy()
        if params and isinstance(params, dict):
            tmp_params = params.copy()

        fp.seek(os.SEEK_SET, os.SEEK_END)
        filesize = fp.tell()
        fp.seek(os.SEEK_SET)
        conn = self._open_conn_to_put_object(bucket, object, filesize, content_type, headers, params)
        totallen = 0
        l = fp.read(self.SendBufferSize)
        retry_times = 0
        while len(l) > 0:
            if retry_times > 100:
                raise Exception('retry too many times')
            try:
                conn.send(l)
                retry_times = 0
            except:
                retry_times += 1
                continue
            totallen += len(l)
            if self.show_bar:
                self.view_bar(totallen, filesize)
            l = fp.read(self.SendBufferSize)
        res = conn.getresponse()
        if res.status == 301 or res.status == 302:
            self.host = helper_get_host_from_resp(res, bucket)
            return self.put_object_from_fp(bucket, tmp_object, fp, content_type, tmp_headers, tmp_params)
        return res

    def get_object(self, bucket, object, headers=None, params=None):
        '''
        Get object

        :type bucket: string
        :param

        :type object: string
        :param

        :type headers: dict
        :param: HTTP header

        Returns:
            HTTP Response
        '''
        method = 'GET'
        body = ''
        return self.http_request(method, bucket, object, headers, body, params)

    def get_object_to_file(self, bucket, object, filename, headers=None):
        '''
        Get object and write the content of object into a file

        :type bucket: string
        :param

        :type object: string
        :param

        :type filename: string
        :param

        :type headers: dict
        :param: HTTP header

        Returns:
            HTTP Response
        '''
        res = self.get_object(bucket, object, headers)
        totalread = 0
        if res.status / 100 == 2:
            header = {}
            header = convert_header2map(res.getheaders())
            filesize = safe_get_element("content-length", header)
            with open(filename, 'wb') as f:
                data = ''
                while True:
                    data = res.read(self.RecvBufferSize)
                    if data:
                        f.write(data)
                        totalread += len(data)
                        if self.show_bar:
                            self.view_bar(totalread, filesize)
                    else:
                        break
        # TODO: get object with flow
        return res

    def delete_object(self, bucket, object, headers=None):
        '''
        Delete object

        :type bucket: string
        :param

        :type object: string
        :param

        :type headers: dict
        :param: HTTP header

        Returns:
            HTTP Response
        '''
        method = 'DELETE'
        body = ''
        params = {}
        return self.http_request(method, bucket, object, headers, body, params)

    def head_object(self, bucket, object, headers=None):
        '''
        Head object, to get the meta message of object without the content

        :type bucket: string
        :param

        :type object: string
        :param

        :type headers: dict
        :param: HTTP header

        Returns:
            HTTP Response
        '''
        method = 'HEAD'
        body = ''
        params = {}
        return self.http_request(method, bucket, object, headers, body, params)

    def post_object_group(self, bucket, object, object_group_msg_xml, headers=None, params=None):
        '''
        Post object group, merge all objects in object_group_msg_xml into one object
        :type bucket: string
        :param

        :type object: string
        :param

        :type object_group_msg_xml: string
        :param: xml format string, like
                <CreateFileGroup>
                    <Part>
                        <PartNumber>N</PartNumber>
                        <FileName>objectN</FileName>
                        <Etag>"47BCE5C74F589F4867DBD57E9CA9F808"</Etag>
                    </Part>
                </CreateFileGroup>
        :type headers: dict
        :param: HTTP header

        :type params: dict
        :param: parameters

        Returns:
            HTTP Response
        '''
        method = 'POST'
        if not headers:
            headers = {}
        if not params:
            params = {}
        if not headers.has_key('Content-Type'):
            content_type = get_content_type_by_filename(object)
            headers['Content-Type'] = content_type
        body = object_group_msg_xml
        params['group'] = ''
        headers['Content-Length'] = str(len(body))
        return self.http_request(method, bucket, object, headers, body, params)

    def get_object_group_index(self, bucket, object, headers=None):
        '''
        Get object group_index

        :type bucket: string
        :param

        :type object: string
        :param

        :type headers: dict
        :param: HTTP header

        Returns:
            HTTP Response
        '''
        if not headers:
            headers = {}
        headers["x-oss-file-group"] = ''
        method = 'GET'
        body = ''
        params = {}
        return self.http_request(method, bucket, object, headers, body, params)

    def upload_part_from_file_given_pos(self, bucket, object, filename, offset, partsize, upload_id, part_number, headers=None, params=None):
        if not params:
            params = {}
        params['partNumber'] = part_number
        params['uploadId'] = upload_id
        content_type = ''
        return self.put_object_from_file_given_pos(bucket, object, filename, offset, partsize, content_type, headers, params)

    def put_object_from_file_given_pos(self, bucket, object, filename, offset, partsize, content_type='', headers=None, params=None):
        '''
        Put object into bucket, the content of object is read from given posision of filename
        :type bucket: string
        :param

        :type object: string
        :param

        :type fllename: string
        :param: the name of the read file

        :type offset: int
        :param: the given position of file

        :type partsize: int
        :param: the size of read content

        :type content_type: string
        :param: the object content type that supported by HTTP

        :type headers: dict
        :param: HTTP header

        Returns:
            HTTP Response
        '''
        tmp_object = object
        tmp_headers = {}
        tmp_params = {}
        if headers and isinstance(headers, dict):
            tmp_headers = headers.copy()
        if params and isinstance(params, dict):
            tmp_params = params.copy()

        fp = open(filename, 'rb')
        if offset > os.path.getsize(filename):
            fp.seek(os.SEEK_SET, os.SEEK_END)
        else:
            fp.seek(offset)
        if not content_type:
            content_type = get_content_type_by_filename(filename)
        conn = self._open_conn_to_put_object(bucket, object, partsize, content_type, headers, params)
        left_len = partsize
        while True:
            if left_len <= 0:
                break
            elif left_len < self.SendBufferSize:
                buffer_content = fp.read(left_len)
            else:
                buffer_content = fp.read(self.SendBufferSize)

            if buffer_content:
                conn.send(buffer_content)

            left_len = left_len - len(buffer_content)

        fp.close()
        res = conn.getresponse()
        if res.status == 301 or res.status == 302:
            self.host = helper_get_host_from_resp(res, bucket)
            return self.put_object_from_file_given_pos(bucket, tmp_object, filename, offset, partsize
, content_type, tmp_headers, tmp_params)
        return res

    def upload_large_file(self, bucket, object, filename, thread_num=10, max_part_num=1000, headers=None):
        '''
        Upload large file, the content is read from filename. The large file is splitted into many parts. It will        put the many parts into bucket and then merge all the parts into one object.

        :type bucket: string
        :param

        :type object: string
        :param

        :type fllename: string
        :param: the name of the read file

        :type thread_num: int
        :param

        :type max_part_num: int
        :param

        :type headers: dict
        :param

        Returns:
            HTTP Response

        '''
        #split the large file into 1000 parts or many parts
        #get part_msg_list
        if not headers:
            headers = {}
        part_msg_list = split_large_file(filename, object, max_part_num)
        #make sure all the parts are put into same bucket
        if len(part_msg_list) < thread_num and len(part_msg_list) != 0:
            thread_num = len(part_msg_list)
        step = len(part_msg_list) / thread_num
        retry_times = self.retry_times
        while(retry_times >= 0):
            try:
                threadpool = []
                for i in xrange(0, thread_num):
                    if i == thread_num - 1:
                        end = len(part_msg_list)
                    else:
                        end = i * step + step
                    begin = i * step
                    oss = OssAPI(self.host, self.access_id, self.secret_access_key)
                    current = PutObjectGroupWorker(oss, bucket, filename, part_msg_list[begin:end], self.retry_times)
                    threadpool.append(current)
                    current.start()
                for item in threadpool:
                    item.join()
                break
            except:
                retry_times = retry_times -1
        if -1 >= retry_times:
            print("after retry %s, failed, upload large file failed!" % retry_times)
            return
        #get xml string that contains msg of object group
        object_group_msg_xml = create_object_group_msg_xml(part_msg_list)
        content_type = get_content_type_by_filename(filename)
        if not headers.has_key('Content-Type'):
            headers['Content-Type'] = content_type
        return self.post_object_group(bucket, object, object_group_msg_xml, headers)

    def copy_object(self, source_bucket, source_object, target_bucket, target_object, headers=None):
        '''
        Copy object

        :type source_bucket: string
        :param

        :type source_object: string
        :param

        :type target_bucket: string
        :param

        :type target_object: string
        :param

        :type headers: dict
        :param: HTTP header

        Returns:
            HTTP Response
        '''
        if not headers:
            headers = {}
        source_object = urllib.parse.quote(source_object)
        headers['x-oss-copy-source'] = "/%s/%s" % (source_bucket, source_object)
        method = 'PUT'
        body = ''
        params = {}
        return self.http_request(method, target_bucket, target_object, headers, body, params)

    def init_multi_upload(self, bucket, object, headers=None, params=None):
        '''
        Init multi upload

        :type bucket: string
        :param

        :type object: string
        :param

        :type headers: dict
        :param: HTTP header

        :type params: dict
        :param: HTTP header

        Returns:
            HTTP Response
        '''
        if not params:
            params = {}
        method = 'POST'
        body = ''
        params['uploads'] = ''
        return self.http_request(method, bucket, object, headers, body, params)

    def get_all_parts(self, bucket, object, upload_id, max_parts=None, part_number_marker=None):
        '''
        List all upload parts of given upload_id
        :type bucket: string
        :param

        :type object: string
        :param

        :type upload_id: string
        :param

        :type max_parts: int
        :param

        :type part_number_marker: string
        :param

        Returns:
            HTTP Response
        '''
        method = 'GET'
        headers = {}
        body = ''
        params = {}
        params['uploadId'] = upload_id
        if max_parts:
            params['max-parts'] = max_parts
        if part_number_marker:
            params['part-number-marker'] = part_number_marker
        return self.http_request(method, bucket, object, headers, body, params)

    def get_all_multipart_uploads(self, bucket, delimiter=None, max_uploads=None, key_marker=None, prefix=None, upload_id_marker=None, headers=None):
        '''
        List all upload_ids and their parts
        :type bucket: string
        :param

        :type delimiter: string
        :param

        :type max_uploads: string
        :param

        :type key_marker: string
        :param

        :type prefix: string
        :param

        :type upload_id_marker: string
        :param

        :type headers: dict
        :param: HTTP header

        Returns:
            HTTP Response
        '''
        method = 'GET'
        object = ''
        body = ''
        params = {}
        params['uploads'] = ''
        if delimiter:
            params['delimiter'] = delimiter
        if max_uploads:
            params['max-uploads'] = max_uploads
        if key_marker:
            params['key-marker'] = key_marker
        if prefix:
            params['prefix'] = prefix
        if upload_id_marker:
            params['upload-id-marker'] = upload_id_marker
        return self.http_request(method, bucket, object, headers, body, params)

    def upload_part(self, bucket, object, filename, upload_id, part_number, headers=None, params=None):
        '''
        Upload the content of filename as one part of given upload_id

        :type bucket: string
        :param

        :type object: string
        :param

        :type filename: string
        :param

        :type upload_id: string
        :param

        :type part_number: int
        :param

        :type headers: dict
        :param: HTTP header

        :type params: dict
        :param: HTTP header

        Returns:
            HTTP Response
        '''
        if not params:
            params = {}
        params['partNumber'] = part_number
        params['uploadId'] = upload_id
        content_type = ''
        return self.put_object_from_file(bucket, object, filename, content_type, headers, params)

    def upload_part_from_string(self, bucket, object, data, upload_id, part_number, headers=None, params=None):
        '''
        Upload the content of string as one part of given upload_id

        :type bucket: string
        :param

        :type object: string
        :param

        :type data: string
        :param

        :type upload_id: string
        :param

        :type part_number: int
        :param

        :type headers: dict
        :param: HTTP header

        :type params: dict
        :param: HTTP header

        Returns:
            HTTP Response
        '''
        if not params:
            params = {}
        params['partNumber'] = part_number
        params['uploadId'] = upload_id
        content_type = ''
        fp = io.StringIO(data)
        return self.put_object_from_fp(bucket, object, fp, content_type, headers, params)

    def complete_upload(self, bucket, object, upload_id, part_msg_xml, headers=None, params=None):
        '''
        Finish multiupload and merge all the parts in part_msg_xml as a object.

        :type bucket: string
        :param

        :type object: string
        :param

        :type upload_id: string
        :param

        :type part_msg_xml: string
        :param

        :type headers: dict
        :param: HTTP header

        :type params: dict
        :param: HTTP header

        Returns:
            HTTP Response
        '''
        if not headers:
            headers = {}
        if not params:
            params = {}
        method = 'POST'
        body = part_msg_xml
        headers['Content-Length'] = str(len(body))
        params['uploadId'] = upload_id
        if not headers.has_key('Content-Type'):
            content_type = get_content_type_by_filename(object)
            headers['Content-Type'] = content_type
        return self.http_request(method, bucket, object, headers, body, params)

    def cancel_upload(self, bucket, object, upload_id, headers=None, params=None):
        '''
        Cancel multiupload and delete all parts of given upload_id
        :type bucket: string
        :param

        :type object: string
        :param

        :type upload_id: string
        :param

        :type headers: dict
        :param: HTTP header

        :type params: dict
        :param: HTTP header

        Returns:
            HTTP Response
        '''
        if not params:
            params = {}
        method = 'DELETE'
        params['uploadId'] = upload_id
        body = ''
        return self.http_request(method, bucket, object, headers, body, params)

    def multi_upload_file(self, bucket, object, filename, upload_id='', thread_num=10, max_part_num=10000, headers=None, params=None):
        '''
        Upload large file, the content is read from filename. The large file is splitted into many parts. It will        put the many parts into bucket and then merge all the parts into one object.

        :type bucket: string
        :param

        :type object: string
        :param

        :type fllename: string
        :param: the name of the read file

        :type upload_id: string
        :param

        :type thread_num: int
        :param

        :type max_part_num: int
        :param

        :type headers: dict
        :param

        :type params: dict
        :param

        Returns:
            HTTP Response
        '''
        #get init upload_id
        if not upload_id:
            res = self.init_multi_upload(bucket, object, headers, params)
            body = res.read()
            if res.status == 200:
                h = GetInitUploadIdXml(body)
                upload_id = h.upload_id
            else:
                err = ErrorXml(body)
                raise Exception("%s, %s" %(res.status, err.msg))
        if not upload_id:
            raise Exception("-1, Cannot get upload id.")
        #split the large file into 1000 parts or many parts
        #get part_msg_list
        part_msg_list = split_large_file(filename, object, max_part_num)
        logger = getlogger(self.debug)
        logger.info("bucket:%s, object:%s, upload_id is: %s, split_number:%d" % (bucket, object, upload_id, len(part_msg_list)))

        #make sure all the parts are put into same bucket
        if len(part_msg_list) < thread_num and len(part_msg_list) != 0:
            thread_num = len(part_msg_list)
        step = len(part_msg_list) / thread_num

        #list part to get a map
        upload_retry_times = self.retry_times
        while(upload_retry_times >= 0):
            uploaded_part_map = {}
            oss = OssAPI(self.host, self.access_id, self.secret_access_key)
            uploaded_part_map = get_part_map(oss, bucket, object, upload_id)
            retry_times = self.retry_times
            while(retry_times >= 0):
                threadpool = []
                try:
                    for i in xrange(0, thread_num):
                        if i == thread_num - 1:
                            end = len(part_msg_list)
                        else:
                            end = i * step + step
                        begin = i * step
                        oss = OssAPI(self.host, self.access_id, self.secret_access_key)
                        current = UploadPartWorker(oss, bucket, object, upload_id, filename, part_msg_list[begin:end], uploaded_part_map, self.retry_times)
                        threadpool.append(current)
                        current.start()
                    for item in threadpool:
                        item.join()
                    break
                except:
                    retry_times -= 1
            if -1 >= retry_times:
                raise Exception("-2, after retry %s, failed, multi upload part failed! upload_id:%s" % (self.retry_times, upload_id))
            #get xml string that contains msg of part
            part_msg_xml = create_part_xml(part_msg_list)
            #complete upload
            res = self.complete_upload(bucket, object, upload_id, part_msg_xml, headers, params)
            if res.status == 200:
                break
            upload_retry_times -= 1
        if upload_retry_times < 0:
            raise Exception("-3, after retry %s, failed, multi upload file failed! upload_id:%s" % (self.retry_times, upload_id))
        return res

    def delete_objects(self, bucket, object_list=None, headers=None, params=None):
        '''
        Batch delete objects
        :type bucket: string
        :param:

        :type object_list: list
        :param:

        :type headers: dict
        :param: HTTP header

        :type params: dict
        :param: the parameters that put in the url address as query string

        Returns:
            HTTP Response
        '''
        if not object_list:
            object_list = []
        object_list_xml = create_delete_object_msg_xml(object_list)
        return self.batch_delete_object(bucket, object_list_xml, headers, params)

    def batch_delete_object(self, bucket, object_list_xml, headers=None, params=None):
        '''
        Delete the objects in object_list_xml
        :type bucket: string
        :param:

        :type object_list_xml: string
        :param:

        :type headers: dict
        :param: HTTP header

        :type params: dict
        :param: the parameters that put in the url address as query string

        Returns:
            HTTP Response
        '''
        if not headers:
            headers = {}
        if not params:
            params = {}
        method = 'POST'
        object = ''
        body = object_list_xml
        headers['Content-Length'] = str(len(body))
        params['delete'] = ''
        base64md5 = base64.encodestring(md5.new(body).digest())
        if base64md5[-1] == '\n':
            base64md5 = base64md5[0:-1]
        headers['Content-MD5'] = base64md5
        return self.http_request(method, bucket, object, headers, body, params)

    def list_objects(self, bucket, prefix=''):
        '''
        :type bucket: string
        :param:

        :type prefix: string
        :param:

        Returns:
            a list that contains the objects in bucket with prefix
        '''
        get_instance = GetAllObjects()
        marker_input = ''
        object_list = []
        oss = OssAPI(self.host, self.access_id, self.secret_access_key)
        (object_list, marker_output) = get_instance.get_object_in_bucket(oss, bucket, marker_input, prefix)
        return object_list

    def batch_delete_objects(self, bucket, object_list=None):
        '''
        :type bucket: string
        :param:

        :type object_list: object name list
        :param:

        Returns:
            True or False
        '''
        if not object_list:
            object_list = []
        object_list_xml = create_delete_object_msg_xml(object_list)
        try:
            res = self.batch_delete_object(bucket, object_list_xml)
            if res.status / 100 == 2:
                return True
        except:
            pass
        return False

    def get_object_info(self, bucket, object, headers=None, params=None):
        '''
        Get object information
        :type bucket: string
        :param:

        :type object: string
        :param:

        :type headers: dict
        :param: HTTP header

        :type params: dict
        :param: the parameters that put in the url address as query string

        Returns:
            HTTP Response
        '''
        if not headers:
            headers = {}
        if not params:
            params = {}
        method = 'GET'
        body = ''
        params['objectInfo'] = ''
        return self.http_request(method, bucket, object, headers, body, params)
