#!/usr/bin/env python
# An IRC bot doing random handy things.

from ircbot import SingleServerIRCBot
from irclib import nm_to_n, nm_to_h, irc_lower, ip_numstr_to_quad, ip_quad_to_numstr, Event

import random, time, datetime


DATADIR = "datadir/"

# Can add lines to a file, and read either certain lines or lines at random.
# XXX: Make it add directories if necessary
# XXX: Make a subclass that makes sure entries are unique.
class ResourceFile:
   def __init__( self, category ):
      self.file = DATADIR + category + ".txt"

   def _slurpText( self ):
      f = file( self.file, 'r' )
      text = f.readlines()
      f.close
      text = map( lambda( line ): line.strip(), text )
      return text

   def getCategory( self ):
      return self.category

   def getLines( self ):
      return self._slurpText()

   def clearFile( self ):
      f = file( self.file, 'w' )
      f.close()

   def addLine( self, line ):
      f = file( self.file, 'a' )
      f.write( line.strip() + "\n" )
      f.close()

   def getLine( self, line ):
      lines = self._slurpText()
      if line < len( lines ):
         return lines[line]

   def getLastLine( self ):
      lines = self._slurpText()
      return lines[len( lines ) - 1]

   def getRandomLine( self ):
      lines = self._slurpText()
      length = len( lines )
      return lines[ random.randint( 0, length-1 ) ]

class MemoFile( ResourceFile ):
   def __init__( self, name ):
      ResourceFile.__init__( self, "memos/" + name )
      # Make sure the file exists, in case it gets opened for reading later.
      f = file( self.file, 'a' )
      f.close()

   def getMemos( self ):
      memos = self._slurpText()
      self.clearFile()
      return memos


class UniqueResourceFile( ResourceFile ):
   def __init__( self, category ):
      ResourceFile.__init__( self, category )

   def addLine( self, line ):
      pass


# XXX: Date and time and such
class Logger:
   def __init__( self, server, channel, category ):
      date = datetime.date.today().isoformat()
      logfilestring = "%s/%s-%s-%s" % (server, channel, date, category)
      self.logfile = ResourceFile( logfilestring )

   def log( self, event ):
      who = nm_to_n( event.source() )
      now = datetime.datetime.now().ctime()
      if event.eventtype() == "pubmsg": 
         text = event.arguments()[0]
         self.logfile.addLine( "%s <%s>\t%s" % (now, who, text) )
      elif event.eventtype() == "ctcp":
         if event.arguments()[0] == "ACTION":
            text = event.arguments()[1]
            self.logfile.addLine( "%s %s %s" % (now, who, text) )



def textAfterColon( text ):
   tac = text.find( ':' )
   if tac >= 0:
      tac += 1
      return text[tac:].strip()
   else:
      return ''

def textBeforeColon( text ):
   tbc = text.find( ':' )
   if tbc >= 0:
      return text[:tbc].strip()
   else:
      return text

# XXX: Possible bugs
# *New logs at midnight!!!  Make sure it works, yaknow.
# *Adding new stuff to the data files!  Especially policies, I think

# XXX: To do
# *Private message handling
# *Make him able to kick people, other admin-y tasks, etc.
# *Exalted EXP calculator!
# *Remember specific links and bits of information until told to forget them
# *More consistant data file handling and adding and such?
# *RP mode --silent, special log, and doesn't absorb actions
# *Doink out duplicate actions, names and policies
# *Memo multiple people at once
# *Backlog system, that sends you the last X lines of text
# *User manual (possibly via PM and auto-generating docs --docstrings?)
# *Set topic name?
# *Remember word of the day, or pick one if none given
# *More in-depth logging... maybe multiple topics at once, with status?  Log
# retrieval, as well?
# *Make users able to edit and correct data files such as murders or weapons
# *URL Logger?
# *Google calculator?
# *Dictionary?
# *Make the quiet and non-quiet commands less... kludgy?
# *Bot status message!  Uptime, tyop's, cookies eaten, dice rolled,
# number and size of logs, etc.
# *File locking?  Multiple channels at once???  Ick...
# *Music?
# *AI...  Markov Chains?  Simple punish/reward system?
class GlennBot(SingleServerIRCBot):
   def __init__(self, nickname, channel, server, port=6667):
      SingleServerIRCBot.__init__(self, [(server, port)], nickname, nickname)
      self.nick = nickname
      self.channel = channel

      self.server = server

      self.commands = {}
      self.quiet = False
      self.wordOfTheDay = "Banana"

      self.generalLogger = Logger( server, channel, "all" )
      self.topicalLogger = False

      self.namexFile = ResourceFile( "namex" )
      self.policyFile = ResourceFile( "policy" )
      self.actionFile = ResourceFile( "actions" )
      self.murderFile = ResourceFile( "murder" )
      self.weaponFile = ResourceFile( "weapons" )

      self.initCommands()
      self.initTimers()



   def initCommands( self ):
      self.commands['dice'] =   self.doDice
      self.commands['roll'] =   self.doDice
      self.commands['damage'] = self.doDamageDice
      self.commands['dmg'] =    self.doDamageDice

      self.commands['start log'] =  self.doStartTopicalLog
      self.commands['logon'] =  self.doStartTopicalLog
      self.commands['stop log'] = self.doStopTopicalLog
      self.commands['logoff'] = self.doStopTopicalLog

      self.commands['namex'] =  self.doName
      self.commands['name'] =   self.doName
      self.commands['new name'] =   self.doNewName
      self.commands['policy'] = self.doPolicy
      self.commands['new policy'] = self.doNewPolicy

      self.commands['action'] = self.doAction
      self.commands['word of the day'] = self.doWOTD
      self.commands['poke']   = self.doPoke

      self.commands['cookie'] =   self.doCookie

      self.commands['quiet'] =self.doToggleQuiet
      #self.commands['hush'] =   self.doToggleQuiet
      self.commands['mimic'] =  self.doMimic
      self.commands['die'] =    self.doDisconnect
      #self.commands['bounce'] = self.doBounce

      self.commands['kill'] =    self.doMurder
      self.commands['murder'] =  self.doMurder
      self.commands['execute'] = self.doMurder
      self.commands['assassinate'] = self.doMurder
      self.commands['new murder'] = self.doNewMurder
      self.commands['new weapon'] = self.doNewWeapon

      self.commands['memo'] =    self.doMemo
      self.commands['message'] = self.doMemo

      self.commands['experience'] = self.doExalt
      self.commands['exalt'] = self.doExalt

   def initTimers( self ): 
      now = datetime.datetime.now()
      endOfDay = now.replace( hour=23, minute=59, second=59 )
      retardoBadKludge = time.mktime( endOfDay.timetuple() )
      self.ircobj.execute_at( retardoBadKludge, self.newDayLog )
      #self.ircobj.execute_delayed( 2, printFoo, [self] )


   # Callbacks and basic functionality
   def on_nicknameinuse(self, c, e):
       c.nick(c.get_nickname() + "_")

   def on_welcome(self, c, e):
       c.join(self.channel)
       print "Joined " + self.channel

   def on_privmsg(self, c, e):
      pass
      #self.parseCommand( e, c, e.arguments()[0] )

   def on_dccmsg(self, c, e):
      pass

   def on_dccchat(self, c, e):
      pass

   def on_ctcp(self, c, e):
        """Default handler for ctcp events.

        Replies to VERSION and PING requests and relays DCC requests
        to the on_dccchat method.
        """
        if e.arguments()[0] == "VERSION":
            c.ctcp_reply(nm_to_n(e.source()),
                         "VERSION " + self.get_version())
        elif e.arguments()[0] == "PING":
            if len(e.arguments()) > 1:
                c.ctcp_reply(nm_to_n(e.source()),
                             "PING " + e.arguments()[1])
        elif e.arguments()[0] == "DCC" and e.arguments()[1].split(" ", 1)[0] == "CHAT":
           self.on_dccchat(c, e)
        elif e.arguments()[0] == "ACTION":
           whofrom = nm_to_n( e.source() )
           print "Action: %s %s" % (whofrom, e.arguments()[1] )
           self.analyzeEntireAction( whofrom, e.arguments()[1] )
           self.log( e )
           self.parseCommand( c, whofrom, e.arguments()[1] )


   def on_pubmsg(self, c, e):
       whofrom = nm_to_n( e.source() )
       self.log( e )
       self.analyzeEntireText( whofrom, e.arguments()[0] )
       self.parseCommand( c, whofrom, e.arguments()[0] )


   # A bit of abstraction, mainly for logging
   def sendMessage( self, message ):
      if not self.quiet:
         e = Event( "pubmsg", self.nick, self.channel, [message] )
         self.connection.privmsg( self.channel, message )
         self.log( e )
         time.sleep( 0.2 )

   def sendAction( self, message ):
      if not self.quiet:
         e = Event( "ctcp", self.nick, self.channel, ["ACTION", message] )
         self.connection.action( self.channel, message )
         self.log( e )
         time.sleep( 0.2 )

   # Start a log for a new day
   def newDayLog( self ):
      self.sendMessage( "(( Starting new log, please wait... ))" )
      time.sleep( 3 )
      self.generalLogger = 0
      self.generalLogger = Logger( self.server, self.channel, "all" )
      self.sendMessage( "(( Done. ))" )

   def log( self, event ):
      self.generalLogger.log( event )
      if self.topicalLogger:
         self.topicalLogger.log( event )

   # XXX: Does not work!
   def changeNick( self, newnick ):
      self.nick = newnick
      self.server.nick( self.nick )

   # A stub for doing things not invoked by a command directly,
   # like text-analysis, spellchecking, etc.
   # These are NOT triggered by things the bot itself does!
   def analyzeEntireText( self, whofrom, text ):
      pass

   def analyzeEntireAction( self, whofrom, text ):
      actionwords = text.split()
      if (len( actionwords ) > 1) and not ('poke' in text) \
            and not (self.nick in text):
         self.actionFile.addLine( text )


   # Thing is, there's two command formats, sorta...  there's the 
   # bot-name-prefixed that makes it seem more conversational, and then
   # there's the !-prefixed type for brevity.
   # Aha.  Both will use the same keyword-matching in the body, but
   # you can replace the bot name with a !.
   # Sauce.
   def parseCommand( self, c, whofrom, cmd ): 
       cmdtext = cmd.lower().strip()
       mynick = self.nick.lower()
       if (cmd[0] == '!') or (cmdtext.find( mynick ) >= 0):
          self.doCommand( whofrom, cmd )

   def doCommand(self, whofrom, cmd):
       print "Doing '" + cmd + "'"
       cmdtext = cmd.lower().strip()

       for command in self.commands:
          if command in cmdtext:
             self.commands[command]( whofrom, cmd )
             return


   # BOT MANAGEMENT
   def doDisconnect( self, whofrom, cmd ):
      if "Icefox" in whofrom:
         self.die( "Aieeeee!" )
      elif "GMfox" in whofrom:
         self.die( "Aieeeee!" )
      elif "GMFox" in whofrom:
         self.die( "Aieeeee!" )
      else:
         self.sendAction( \
               "taps one white mana to become immune to non-foxes." )


   #def doBounce( self, whofrom, cmd ):
   #   self.disconnect()

   def doToggleQuiet( self, whofrom, cmd ):
      if self.quiet:
         #self.changeNick( self.nick[1:] )
         self.quiet = False
         self.sendMessage( "Whew, I can talk again!" )
      else:
         #self.changeNick( "Q" + self.nick )
         self.sendMessage( "Shutting up, sir." )
         self.quiet = True

   def doMimic( self, whofrom, cmd ):
      text = textAfterColon( cmd )
      if text != '':
         self.sendMessage( text )

   # LOGGING
   def doStartTopicalLog( self, whofrom, cmd ):
      text = textAfterColon( cmd )
      if text != '':
         if self.topicalLogger:
            self.doStopTopicalLog( whofrom, cmd )
         self.sendMessage( "%s started new log %s" % (whofrom, text) )
         self.topicalLogger = Logger( self.server, self.channel, text )
      else:
         self.sendMessage( "Expected: 'start log: logname'" )

   def doStopTopicalLog( self, whofrom, cmd ):
      if self.topicalLogger:
         self.sendMessage( "Log %s stopped by %s" % \
               (self.topicalLogger.getCategory(), whofrom) )
         self.topicalLogger = False

   # MEMOS
   def doMemo( self, whofrom, cmd ):
      memo = textAfterColon( cmd )
      # No new memos, give them old ones
      if memo == '':
         f = MemoFile( whofrom )
         memos = f.getMemos()
         if memos == []:
            self.sendMessage( whofrom + ", you have no memos." )
         else:
            self.sendMessage( whofrom + "'s memos:" )
            for x in memos:
               self.sendMessage( x )
               # A bit of flood control
               time.sleep( 0.2 )
            self.sendMessage( "Done" )
      else:
         commandlist = textBeforeColon( cmd ).split()
         whoto = commandlist[-1]
         f = MemoFile( whoto )
         now = datetime.datetime.now().ctime()
         f.addLine( "From %s at %s:  %s" % (whofrom, now, memo) )
         self.sendMessage( "So noted." )



   # DICE
   def doDice( self, whofrom, cmd ):
      c = self.connection
      cmd = cmd.split()
      for x in cmd:
         if x.isdigit():
            x = int( x )
            if x < 0 or x > 100:
               self.sendMessage( "Shyeah... right." )
               return
            rolls = ""
            successes = 0
            for i in range( int( x ) ):
               roll = random.randint( 1, 10 )
               if roll >= 7: successes += 1
               if roll == 10: successes += 1
               rolls += str( roll ) + " "
            message = "%s, you got %d successes.  Rolled %s" % \
                  (whofrom, successes, rolls)
            self.sendMessage( message  )
            break

   def doDamageDice( self, whofrom, cmd ):
      c = self.connection
      cmd = cmd.split()
      for x in cmd:
         if x.isdigit():
            x = int( x )
            if x < 0 or x > 100:
               self.sendMessage( "No way!" )
               return
            rolls = ""
            successes = 0
            for i in range( int( x ) ):
               roll = random.randint( 1, 10 )
               if roll >= 7: successes += 1
               rolls += str( roll ) + " "
            message = "%s, you did %d damage.  Rolled %s" % \
                  (whofrom, successes, rolls)
            self.sendMessage( message  )

   # OTHER STUFF
   def doName( self, whofrom, cmd ):
      l = self.namexFile.getRandomLine()
      self.sendMessage( "A good name is " + l )

   def doNewName( self, whofrom, cmd ):
      text = textAfterColon( cmd )
      self.namexFile.addLine( text )

   def doPolicy( self, whofrom, cmd ):
      l = self.policyFile.getRandomLine()
      self.sendMessage( whofrom + ", you should " + l )

   def doNewPolicy( self, whofrom, cmd ):
      text = textAfterColon( cmd )
      self.policyFile.addLine( text )
      self.sendMessage( "I am now wiser and more able to serve you, Master." )

   def doCookie( self, whofrom, cmd ):
      self.sendMessage( "Yay, cookies!" )
      self.sendAction( "noms!" )

   def doAction( self, whofrom, cmd ):
      self.sendAction( self.actionFile.getRandomLine() )

   def doExalt( self, whofrom, cmd ):
      self.sendMessage( "Exalted stuff: http://cec.wustl.edu/~snh1/exalt.html" )

   # XXX: Random words?  Remember them over reboots?
   def doWOTD( self, whofrom, cmd ):
      text = textAfterColon( cmd )
      if text != '':
         self.wordOfTheDay = text
         self.sendMessage( "I am now contemplating the mysteries of " + text )
      else:
         self.sendMessage( "The word of the day is: " + self.wordOfTheDay )


   def doPoke( self, whofrom, cmd ):
      selector = random.random()
      if selector > 0.85:
         self.sendAction( "pokes " + whofrom + " back." )
      elif selector > 0.05:
         self.doAction( whofrom, cmd )
      elif selector > 0.04:
         self.sendAction( "briefly turns into a lemur." )
         self.sendMessage( "FRINKFRINKFRINK *WHEOOOOO*!!" )
      else:
         self.sendAction( "goes ballistic from the excessive poking, and sets off his built-in five-kiloton nuke." )
         self.die( "KABOOM!" )



   # XXX: Incomplete...
   # Can we make a good random-death list using both person and weapon?
   # I think so.  It doesn't have to be too large.
   def doMurder( self, whofrom, cmd ):
      choice = random.random()
      weapon = self.weaponFile.getRandomLine()
      # Kill the orderer
      if choice > 0.95:
         weapon = self.weaponFile.getRandomLine()
         self.sendAction( \
               "gets out his %s and gives %s a gruesome end.  Pushy bastard." \
               % (weapon, whofrom) )

      # See: http://drmcninja.com/page.php?pageNum=40&issue=10
      elif choice > 0.90:
         self.sendMessage( "KNIIIIIIFE EEEEEYYYYE ATTAAAACK!!" )
         self.sendAction( "kills everyone with knife-eye ninjutsu." )
      # Kill a random person.
      elif choice > 0.10:
         people = self.channels[self.channel].users()
         person = random.randint( 0, len( people ) - 1 )
         person = people[person]
         deathaction = self.murderFile.getRandomLine()
         try:
            self.sendAction( deathaction % (person, weapon) )
         except TypeError, x:
            self.sendMessage( "Ouch!  Invalid murder file entry!  It needs two '%s' sequences in it for person and weapon." )
            self.doMemo( self.nick, "Icefox: Invalid murder file entry." )

      # Do something else entirely.
      else:
         self.doAction( whofrom, cmd )

      # Appropriate addendum
      if random.random() > 0.95:
         self.sendAction( "can't live with what he's done, and takes his own life!" )
         self.die( "NOOOOOOOO!" )

   def doNewMurder( self, whofrom, cmd ):
      text = textAfterColon( cmd )
      self.murderFile.addLine( text )
      self.sendMessage( "Thank you for teaching me this new technique with which to brutally destroy all who oppose me." )

   def doNewWeapon( self, whofrom, cmd ):
      print "Weapon: " + cmd
      text = textAfterColon( cmd )
      print text
      self.weaponFile.addLine( text )
      self.sendMessage( "Oooo, I can't wait to try out my shiny new " + text + "!" )


###  End of GlennBot!


def main():
   import sys
   if len(sys.argv) != 3:
      print "Usage: %s <server[:port]> <channel>" % sys.argv[0]
      sys.exit(1)

   s = sys.argv[1].split(":", 1)
   server = s[0]
   if len(s) == 2:
      try:
         port = int(s[1])
      except ValueError:
         print "Error: Erroneous port."
         sys.exit(1)
   else:
      port = 6667
   channel = sys.argv[2]

   print "Starting glennbot.py..."
   bot = GlennBot( "George", channel, server, port)
   bot.start()
   bot.sendMessage( "I live!  Praise Zarqon!" )

if __name__ == "__main__":
   main()
