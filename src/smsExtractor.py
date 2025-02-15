#!/usr/bin/env python3
#===============================================================================
#   smsExtractor.py     |   Version 1.2     |   FreeBSD License |   2015-09-14
#   James Hendrie       |   hendrie.james@gmail.com
#
#   Description:
#       Simple script that extracts SMS and MMS messages from previously
#       generated XML files into a subdirectory named after the given file.
#
#   Restrictions:
#       The files are assumed to have been generated by the Android app
#       'SMS Backup & Restore' by Ritesh Sahu.  It's also designed to be used
#       on a Unix-like system, specifically GNU/Linux.
#===============================================================================

import sys, os
import binascii, sqlite3



def directory_setup( filename ):
    ##  Create the top-level directory into which we extract the messages
    try:
        os.mkdir( "%s.d" % filename )

    except PermissionError:
        print( "ERROR:  Could not create directory '%s.d'.  Aborting." %
                filename )
        sys.exit( 1 )

    except FileExistsError:
        print( "WARNING:  Directory '%s.d' exists:  Skipping" % filename )
        return( None, None, True )

    ##  Make the subdirectories
    fDir = os.path.join( "%s.d" % filename, "files" )
    mDir = os.path.join( "%s.d" % filename, "messages" )
    os.mkdir( fDir )
    os.mkdir( mDir )

    ##  Return the directories or quit if they couldn't be made
    if os.path.exists( mDir ) and os.path.exists( fDir ):
        return( mDir, fDir, False )
    else:
        print("ERROR:  Could not create subdirectories.  Aborting.")
        os.rmdir( "%s.d" % filename )
        sys.exit( 1 )



def extract( filename, c ):
    """
    Extract all of the entries from a file opened using 'filename'.  All of the
    content is placed into database 'db', accessed using cursor 'c'.
    """

    ##  Report progress
    print( "Extracting content from '%s'..." % filename )

    ##  Open the file, read it, close it
    fp = open( filename, "r" )
    lines = fp.readlines()
    fp.close()


    for l in lines:
        if "<sms protocol" in l:

            ##  Grab usable information from metadata
            address = l.partition( 'address="' )[2].partition( '"' )[0]
            date = int( l.partition( 'date="' )[2].partition( '"' )[0] )
            rDate = l.partition( 'readable_date="' )[2].partition( '"' )[0]
            body = l.partition( 'body="' )[2].partition( '" toa=' )[0]
            mType = l.partition( 'type="' )[2].partition( '"' )[0]
            name = l.partition( 'name="' )[2].partition( '"' )[0]

            address = address.replace( '+', '' )
            if( len( address ) > 9 ):
                address = address[ ( len(address) ) - 10 : ]

            ##  Put all of the information into a tuple
            stuff = ( "sms", address, mType, date, rDate, name, body,
                    None, "null")

            ##  Put it into the database
            c.execute("""insert into messages values(?,?,?,?, ?, ?, ?, ?, ?)""",
                    stuff )


        if( "image/jpeg" in l or "image/png" in l or "image/gif" in l or
                "video/3gpp" in l):
            ##  Counters
            vidCount = 0
            imageCount = 0

            ##  Get the proper extension
            extension = l.partition( 'ct="' )[2].partition( '"' )[0]
            extension = extension.partition( '/' )[2]

            if extension == "3gpp":
                extension = "3gp"
            elif extension == "jpeg":
                extension = "jpg"

            ##  Metadata is a couple lines up
            index = lines.index( l )
            meta = lines[ index - 3 ]
            prevLine = lines[ index - 1 ]
            nextLine = lines[ index + 1 ]

            ##  Grab information from the metadata
            address = meta.partition( 'address="' )[2].partition( '"' )[0]
            date = meta.partition( 'date="' )[2].partition( '"' )[0]
            rDate = meta.partition( 'readable_date="' )[2].partition( '"' )[0]
            name = meta.partition( 'contact_name="' )[2].partition( '"' )[0]

            ##  Find the mType using the m_size value; null means outgoing,
            ##  anything else was received
            if meta.partition( 'm_size="' )[2].partition( '"' )[0] == "null":
                mType = '1'
            else:
                mType = '2'

            ##  Fix address string
            address = address.replace( '+', '' )
            if( len( address ) > 9 ):
                address = address[ ( len(address) ) - 10 : ]


            ##  Name the file source properly... more or less
            if extension == "3gp":
                src = prevLine.partition( 'video src="' )[2].partition( '"' )[0]
                if src == "":
                    vidCount += 1
                    src = "vid_%03d.3gp" % vidCount
            else:
                src = prevLine.partition( 'img src="' )[2].partition( '"' )[0]
                if src == "":
                    imageCount += 1
                    src = "img_%03d.%s" % ( imageCount, extension )

            ##  If they sent a message with the MMS
            if 'text="' in nextLine:
                body = nextLine.partition( 'text="' )[2].partition( '"' )[0]
            else:
                body = ""

            ##  Turn the MMS base64 text into usable binary data
            dataText = l.partition( 'data="' )[2].partition( '"' )[0]
            data = binascii.a2b_base64( dataText )

            ##  Put it all into a tuple
            stuff = ( "mms", address, mType, date, rDate, name, body,
                    data, src )

            ##  STUFF THAT FUCKER INTO THE DATABASE
            c.execute("""insert into messages values(?, ?,?,?,?, ?, ?, ?, ?)""",
                    stuff )



def print_help():
    print( "Usage:  smsExtractor.py FILE.xml" )
    print( """
This script extracts SMS messages and MMS files (jpg, png or 3gp) from a given
XML file, as they're read, into a subdirectory named after the file in question.
Data extracted from "mms.xml" will go into "mms.xml.d", as an example.

NOTE:
This script assumes files generated by the Android app "SMS Backup & Restore" by
Ritesh Sahu.  It isn't guaranteed nor even expected to work with anything else.

You can find his program at either of the following sites:

(Developer's site)
http://android.riteshsahu.com/apps/sms-backup-restore

(Google Play store)
https://play.google.com/store/apps/details?id=com.riteshsahu.SMSBackupRestore


Options:
    -h or --help:       This help text
    -V or --version:    Version and author info.
    -s or --subdirs:    Write files to individual subdirectories per each contact.""" )



def print_version():
    print( "smsExtractor.py, version 1.2" )
    print( "James Hendrie <hendrie.james@gmail.com>" )



def write_messages( filename, mDir, fDir, c, subdirs ):

    ##  Grab all of the stuff from the database
    c.execute( """select * from messages order by date""" )
    data = c.fetchall()

    ##  Get the addresses, get the names, see if we've got any MMS files
    addresses = []
    names = {}
    filesPresent = False
    for d in data:
        if filesPresent is False and d[7] is not None:
            filesPresent = True

        if d[1] not in addresses:
            addresses.append( d[1] )
            names[ d[1] ] = d[5]

    ##  If there are no files, remove the files subdirectory
    if not filesPresent:
        os.rmdir( fDir )

    print( "Found %i pieces of data total with %i unique addresses" % ( len( data ), len( addresses ) ) )

    ##  Start up a couple of counters
    smsCount = 0
    mmsCount = 0

    print( "Writing Message Text." )
    ##  Write all of the text messages to disk
    for a in addresses:

        messages = []

        ##  Go through each row of data for this address, formatting the message
        for d in data:
            if d[1] == a:
                ##  The top bar consists of 'sent/received' and the date
                msg = ( 80 * '=' ) + '\n'
                if d[2] == "1":
                    msg += "Received on %s\n" % d[4]
                elif d[2] == "2":
                    msg += "Sent on %s\n" % d[4]
                else:
                    msg += "%s\n" % d[4]
                msg += ( 80 * '-' ) + '\n'

                ##  The body (actual content) of the text
                msg += "%s\n\n" % d[6]

                ##  If it had an image or whatever attached, let the user know
                ##  and indicate which file it is
                if d[0] == "mms":
                    msg += "Image:  %s\n" % d[8]

                ##  Cap it off with a bit of padding and add it to the list
                msg += "\n\n"
                messages.append( msg )


        ##  Go through the messages list and write them to the file
        if len( messages ) > 0:
            ##  Files are named using an 'ADDRESS_NAME.txt' convention
            fp = open( os.path.join( mDir, "%s_%s.txt" % ( a, names[a] ) ), "w" )

            ##  Write file to disk
            for m in messages:

                ##  Increment the counter and write text to the file
                smsCount += 1
                fp.write( m )

            fp.close()

    print( "Writing Message Data." )
    ##  Write all of the MMS files to disk
    for d in data:
        a = d[1]
        ##  If it's actually an MMS file
        if filesPresent and d[0] == "mms" and d[7] != None:
            ##  Increment counter
            mmsCount += 1
            if subdirs:
                fSubDir = os.path.join( fDir, "%s_%s" % ( a, names[a] ) )
                if not os.path.exists( fSubDir ):
                    os.mkdir( fSubDir )
            else:
                fSubDir = fDir

            ##  Open the file for binary writing, write the data, close the file
            fp = open( os.path.join( fSubDir, d[8] ), "wb")
            fp.write( d[7] )
            fp.close()

    ##  Correct the numbers a bit
    smsCount -= mmsCount

    ##  Report success
    print( "%s:  %d SMS and %d MMS (total:  %d)" %
            ( filename, smsCount, mmsCount, smsCount + mmsCount ))



def create_database():
    ##  Connect to a database that exists in RAM
    db = sqlite3.connect( ":memory:" )
    c = db.cursor()

    ##  Future reference:
    #   0   type            sms or mms
    #   1   address         phone number
    #   2   mType           Arbitrary sender/receiver value, 1 means the
    #                       other person, 2 means 'me'
    #   3   date            Date (ctime or similar, unreadable to humans)
    #   4   readableDate    Date that people can read
    #   5   name            Contact name
    #   6   body            Message text
    #   7   data            MMS data (image, video, etc.)
    #   8   src             Data source, used as the name of the file

    c.execute( """create table messages( type text, address text, mType text, date text, readableDate text, name text, body text, data blob, src text)""" )

    return( db, c )



def main():
    subdirs = False
    if len( sys.argv ) == 1:
        print( "ERROR:  Require an SMS/MMS file to extract from" )
        sys.exit( 1 )
    else:
        for arg in sys.argv[1:]:
            ##  If they want help
            if arg in ( "-h", "--help" ):
                print_help()
                sys.exit( 0 )
            
            ##  If they want version/author info
            if arg in ( "-V", "--version" ):
                print_version()
                sys.exit( 0 )
            
            if arg in ( "-s", "--subdirs" ):
                subdirs = True
            
            ##  Normal operation
            else:
                ##  Create the directories so that every will be tidy
                mDir, fDir, skip = directory_setup( arg )

                ##  If we were successful
                if not skip:
                    ##  Create the database to store all the info
                    db, cursor = create_database()

                    ##  Extract eveything into database
                    extract( arg, cursor )

                    ##  Write all of the messages to disk
                    write_messages( arg, mDir, fDir, cursor, subdirs )

                    ##  Close the database and cap off the output with a newline
                    db.close()
                    print("")



if __name__ == "__main__":
    main()
