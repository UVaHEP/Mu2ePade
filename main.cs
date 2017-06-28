using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Globalization;
using System.Net.Sockets;
using System.IO;
using System.Xml; 

namespace FEB
{


    public static class Program
    {




	public static void Main(string[] args)
	{
	    var host = "128.143.196.217";
	    var port = 5001; 
		
	    System.Console.WriteLine("I have begun!"); 
	    var regs = padeRegs.loadRegisterTableFromFile("superpaderegs.xml");
//	    FEB_Register.printer m = (string msg) => System.Console.WriteLine("Starting List\r\n--------------------");

//	    m+= (string msg) => System.Console.WriteLine("--------------------\r\nFinished with List");
//	    m("Start!"); 
	    Socket TNETSocket; 
	    var client = new TcpClient(); 
	    TNETSocket = client.Client;
	    TNETSocket.ReceiveBufferSize = 5242880*4-1;
	    TNETSocket.SendBufferSize = 32000;
	    TNETSocket.ReceiveTimeout = 1;
	    TNETSocket.SendTimeout = 1;
	    TNETSocket.NoDelay = true;
	    TNETSocket.Blocking = true; 
	    try { 
		TNETSocket.Connect(host, port);
	    }
	    catch (SocketException e) {
		System.Console.WriteLine("Socket Error: {0}", e); 
		
		return; 
	    }
	    catch (ArgumentOutOfRangeException e) {
		System.Console.WriteLine("Bad Port Argument: {0}", e);
		return; 
	    }
	    catch {
		System.Console.WriteLine("Other Failure"); 
	    }
       
	    foreach (string s in regs.Keys) {
		System.Console.WriteLine("\r\nRegister for key:{0}", s);
		var reg = regs[s];
		if (reg.width == 16) {
		    System.Console.WriteLine("Reading Address....{0}",reg.addr); 
		    var read = String.Format("rd {0}\r\n",reg.addr);
		    TNETSocket.Send(Encoding.ASCII.GetBytes(read)); 

		    while (TNETSocket.Available == 0) {

		    }
		    byte[] buf = new byte[TNETSocket.Available]; 
		    TNETSocket.Receive(buf);
		    System.Console.WriteLine("Bytes....{0}",Encoding.ASCII.GetString(buf));
		}
		if (reg.width == 32) {
		    System.Console.WriteLine("Reading Addresses....{0},{1}",reg.addr, reg.upper_addr); 
		    var readlower = String.Format("rd {0}\r\n",reg.lower_addr);
		    var readupper = String.Format("rd {0}\r\n",reg.upper_addr);
		    TNETSocket.Send(Encoding.ASCII.GetBytes(readlower));
		    while (TNETSocket.Available == 0) {

		    }
		    byte[] buf = new byte[TNETSocket.Available]; 
		    TNETSocket.Receive(buf);
		    System.Console.WriteLine("Bytes....{0}",Encoding.ASCII.GetString(buf));
		    TNETSocket.Send(Encoding.ASCII.GetBytes(readupper));
		    while (TNETSocket.Available == 0) {

		    }
		    buf = new byte[TNETSocket.Available]; 
		    TNETSocket.Receive(buf);
		    System.Console.WriteLine("Bytes....{0}",Encoding.ASCII.GetString(buf));
			}

	    }
	    
	    TNETSocket.Close(); 
	
	}

    }





    public class FEB_Register
    {
	
	public delegate double Conv_to_Double(UInt32 val);
	public delegate UInt32 Conv_from_Double(double v);
	public delegate void printer(string msg);
	
	public string name;
	public string comment;
	public string[] bit_comment;
	public UInt16 addr;
	public UInt16 fpga_offset_mult=0x400;
	public UInt16 fpga_index=0;
	public uint width = 16;
	public UInt16 upper_addr;
	public UInt16 lower_addr;
	public UInt32 prev_val = 0;
	public UInt32 val = 0;
	public double dv = 0;
	public bool pref_hex = false;
	public bool pref_double = false;
	//public Conv_to_Double myUint2Double = Simple_Conv2Double;
	public enum RegError { Unknown, Timeout }

	public void print() {
	    System.Console.WriteLine("name: {0}", name);
	    System.Console.WriteLine("comment: {0}", comment);
	    System.Console.WriteLine("bit_comment: {0}", bit_comment);
	    System.Console.WriteLine("addr: {0}", addr);
	    System.Console.WriteLine("fpga_offset_mult: {0}", fpga_offset_mult);
	    System.Console.WriteLine("fpga_index: {0}", fpga_index);
	    System.Console.WriteLine("width: {0}", width);
	    System.Console.WriteLine("upper_addr: {0}", upper_addr);
	    System.Console.WriteLine("lower_addr: {0}", lower_addr);
	    System.Console.WriteLine("prev_val: {0}", prev_val);
	    System.Console.WriteLine("val: {0}", val);
	    System.Console.WriteLine("dv: {0}", dv);
	    System.Console.WriteLine("pref_hex: {0}", pref_hex);
	    System.Console.WriteLine("pref_double: {0}", pref_double);

	}
	
    }


    
    public class padeRegs
    {
	public static Dictionary<string, FEB_Register> loadRegisterTableFromFile(string fname = "")
	{ 
	    if (fname == "")
		return null;  
	    Dictionary<string, FEB_Register> regTable = new Dictionary<string, FEB_Register>(); 
	    
	    //Try to open the file, if we fail return null 
	    XmlDocument doc = new XmlDocument ();
	    doc.Load (fname); 
	    XmlNode root = doc.DocumentElement; 
	    var en = root.GetEnumerator ();

	    XmlElement e; 
	    XmlAttribute attr; 

	    XmlAttribute name; 
	    XmlAttribute addr;
	    XmlAttribute fpgaOffsetMult;
	    XmlAttribute prefHex;
	    XmlAttribute comment;
	    XmlAttribute bitComment;
	    XmlAttribute width;
	    XmlAttribute upperAddr;
	    XmlAttribute lowerAddr;

	    while (en.MoveNext ()) { 

		e = (XmlElement)en.Current;
		attr = e.GetAttributeNode ("Name"); 
		if (attr != null) {
		    FEB_Register reg = new FEB_Register (); 
		    name = e.GetAttributeNode ("Name"); 
		    addr = e.GetAttributeNode ("Address"); 
		    fpgaOffsetMult = e.GetAttributeNode ("FPGAOffsetMultiplier"); 
		    prefHex = e.GetAttributeNode ("PrefHex"); 
		    comment = e.GetAttributeNode ("Comment");
		    bitComment = e.GetAttributeNode ("BitComments");
		    width = e.GetAttributeNode ("Width"); 
		    upperAddr = e.GetAttributeNode ("UpperAddress"); 
		    lowerAddr = e.GetAttributeNode ("LowerAddress"); 

		    reg.name = name.Value;
		    reg.addr = Convert.ToUInt16 (addr.Value); 
		    reg.fpga_offset_mult = Convert.ToUInt16 (fpgaOffsetMult.Value); 
		    reg.pref_hex = Convert.ToBoolean (prefHex.Value); 
		    reg.comment = comment.Value; 
		    reg.bit_comment = bitComment.Value.Split ('!'); 
		    reg.width = Convert.ToUInt32 (width.Value);
		    reg.upper_addr = Convert.ToUInt16 (upperAddr.Value);
		    reg.lower_addr = Convert.ToUInt16 (lowerAddr.Value); 

		    regTable [reg.name] = reg;

		}
	    }

	    return regTable; 

	}


    }
}
