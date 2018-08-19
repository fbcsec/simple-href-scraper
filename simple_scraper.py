#!/usr/bin/env python3
"""
Simple HREF scraper. Uses Beautiful Soup to pull all of the hrefs from a
document. The URLs are then filtered based on a simple comma-separated
list of file extensions. Finally urllib is used to get and write the files
to a specified directory. See this_script.py -h for options.
"""

import argparse
from collections import OrderedDict
import datetime
import hashlib
from time import sleep
from urllib.request import Request, urlopen, urlretrieve
import os
from bs4 import BeautifulSoup


def argparse_factory():
    """Build argparse object and return parsed argv."""
    parser = argparse.ArgumentParser()
    parser.add_argument("target_url", help="The URL you intend to scrape.", type=str)
    parser.add_argument("destination_directory", help="The directory to dump scraped files in.", type=str)
    parser.add_argument("-d", "--debug", help="Enable debugging output.", action="store_true")
    parser.add_argument("-f", "--file-types", help=("A comma separated list of file extensions to grab."
                                                    " Default set: jpg,jpeg,png,gif,wav,wmv,mp3,flac,mkv,avi,"
                                                    "flv,swf,mp4,webm,pdf,mobi,zip,rar"),
                        nargs='?',
                        default="jpg,jpeg,png,gif,wav,wmv,mp3,flac,mkv,avi,flv,swf,mp4,webm,pdf,mobi,zip,rar")
    parser.add_argument("-s", "--silent", help="Silent mode, produce no output.", action="store_true")
    parser.add_argument('-e', '--halt-error', help="Halt on non-fatal download errors.", action="store_true")
    parser.add_argument('-D', '--dry-run', help="Scrape pages but don't download any files", action='store_true')
    parser.add_argument('-w', '--wait-time', help="Amount of time to wait between downloads."
                                                  " Increasing this can help with target servers that are rate limited"
                                                  " and with ensuring that the modification date on output files"
                                                  " are correct. Default is 1, set to 0 to not wait.",
                        nargs='?',
                        default='1')
    return parser.parse_args()


def check_if_valid_path(path, debug=False):
    """Check if destination path is valid by attempting to open a file in it. Returns true or forces an exit."""
    filename = str(str(hashlib.md5(str(datetime.datetime.now()).encode('utf-8')).hexdigest()[0:10]))
    if debug:
        print("Checking if path is valid by touching %s" % path + '/' + filename)
    try:
        with open(path + '/' + filename, 'x'):
            if debug:
                print("Successfully opened test file.")
                print("Deleting test file...")
            os.unlink(path + '/' + filename)
            return True
    except BaseException as ex:
        if debug:
            print(ex)
        raise SystemExit('Error, could not write to destination directory %s' % path)


def get_target_html(url, debug=False):
    """Obtain the raw html of the page we want to scrape. Returns the html or forces an exit."""
    try:
        if debug:
            print("Attempting to fetch %s" % url)
        req = Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64; rv:56.0) Gecko/20100101 '
                                                  'Firefox/56.0'})
        with urlopen(req) as response:
            if debug:
                print(str(response.info()))
            html = response.read()
            return html
    except BaseException as ex:
        if debug:
            print(ex)
        raise SystemExit("Error, could not connect to target %s" % url)


def find_hotlinks(html, exts='*', debug=False):
    """Build a list of all the href targets in an html document. Then filters the list """
    hotlinks = list()
    filtered_list = list()

    soup = BeautifulSoup(html, 'html.parser')
    if debug:
        print('Finding hrefs.')
    for link in soup.find_all(href=True):
        hotlinks.append(link['href'])
    deduped_hotlinks = list(OrderedDict.fromkeys(hotlinks))
    if exts is not '*':
        exts = exts.split(',')
        if debug:
            print('Passed good extensions: ')
            print(exts)
        for link in deduped_hotlinks:
            link_ext = link.split(".")[-1::][0]
            if debug:
                print('Checking ' + link)
                print('Split: ')
                print(link_ext)
            if link_ext in exts:
                filtered_list.append(link)
    else:
        filtered_list = deduped_hotlinks

    if debug:
        for link in filtered_list:
            print("\t%s" % link)

    return filtered_list


def check_and_fix_protocol(original_target, urls, debug=False):
    """Read a list of URLs and ensure they have a protocol associated with them.
    If the protocol is missing, match the protocol to a target URL.
    Return a new list containing the verified URLs."""
    fixed_urllist = list()
    protocol = original_target.split(':')[0]
    for link in urls:
        if ":" in link:
            if debug:
                print("Link has protocol information: %s" % link)
            fixed_urllist.append(link)
        else:
            if debug:
                print("Link missing protocol information.")
            # Assume a url prefixed by '//' (missing protocol) should be
            # accessed with the same protocol as the original url.
            protocol_added = protocol + ":" + link
            fixed_urllist.append(protocol_added)
            if debug:
                print("New link: %s" % protocol_added)
    return fixed_urllist


def download_file(url, destination_dir, debug=False, silent=False, halt_on_error=False, dry_run=False, wait_time=0):
    """Download file and write to destination_dir while handling errors.
    Practically a frontend to urllib.request.urlretrieve()."""
    filename = url.split("/")[-1]
    full_path = destination_dir + "/" + filename
    if not silent:
        print("[+] Downloading %s to %s..." % (url, full_path))
    try:
        if not dry_run:
            res = urlretrieve(url, full_path)
            sleep(wait_time)
            if debug:
                print(res)
        else:
            if not silent:
                print("[!] Dry Run, no file saved!")
        if not silent:
            print("[+] Done.")
        return True
    except BaseException as ex:
        if debug:
            print(ex)
        if halt_on_error:
            raise SystemExit("Download failed and halt on error set, halting." % url)
        else:
            if not silent:
                print("[-] Download Failed" % url)
            return False


def main():
    args = argparse_factory()
    TARGET_URL = args.target_url
    OUTPUT_DIR = args.destination_directory
    DEBUG_MODE = args.debug
    EXT_LIST = args.file_types
    SILENT = args.silent
    HALT_NONFATAL = args.halt_error
    DRY_RUN = args.dry_run
    WAIT_TIME = int(args.wait_time)

    if DEBUG_MODE:
        print('[!] DEBUG mode on.')
        print('Arguments object:')
        print("\t" + str(args))

    if not SILENT:
        print('[+] Scraping %s' % TARGET_URL)
        print('[+] Saving to %s' % OUTPUT_DIR)

    check_if_valid_path(OUTPUT_DIR, debug=DEBUG_MODE)
    html = get_target_html(TARGET_URL, debug=DEBUG_MODE)
    found_hotlinks = find_hotlinks(html, exts=EXT_LIST, debug=DEBUG_MODE)
    links_to_download = check_and_fix_protocol(TARGET_URL, found_hotlinks, debug=DEBUG_MODE)
    if not SILENT:
        print('[+] Found %d hotlinks.' % len(links_to_download))
        for link in links_to_download:
            print("\t%s" % link)
        print("\n")

    for link in links_to_download:
        download_file(link, OUTPUT_DIR, debug=DEBUG_MODE,
                      silent=SILENT, halt_on_error=HALT_NONFATAL,
                      dry_run=DRY_RUN, wait_time=WAIT_TIME)


if __name__ == "__main__":
    main()
