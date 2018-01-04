package org.wfrobotics;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Scanner;

import org.wfrobotics.reuse.subsystems.vision.*;
import org.wfrobotics.reuse.subsystems.vision.messages.VisionMessageConfig;
import org.wfrobotics.reuse.subsystems.vision.messages.VisionMessageTargets;

public class Test implements CameraServer.CameraListener
{
   public static void main(String args[])
   {
      CameraServer cameraServer = CameraServer.getInstance();
      
      cameraServer.SetConfig(new VisionMessageConfig(0,1,
              new ArrayList<>(Arrays.asList(new Boolean[] {true, false}))));
      
      Test listener = new Test();
      
      cameraServer.AddListener(listener);


      Scanner cc = new Scanner(System.in);
      try {
	      while(true)
	      {
	          String txt = cc.nextLine();
	          switch (txt) {
	              case "0":
	                  cameraServer.SetConfig(new VisionMessageConfig(0,0,
	                          new ArrayList<>(Arrays.asList(new Boolean[] {true, false}))));
	                  break;
	
	              case "1":
	                  cameraServer.SetConfig(new VisionMessageConfig(1,1,
	                          new ArrayList<>(Arrays.asList(new Boolean[] {false, true}))));
	                  break;
	
	              case "2":
	                  cameraServer.SetConfig(new VisionMessageConfig(0,1,
	                          new ArrayList<>(Arrays.asList(new Boolean[] {true, false}))));
	                  break;
	
	              case "3":
	                  cameraServer.SetConfig(new VisionMessageConfig(1,0,
	                          new ArrayList<>(Arrays.asList(new Boolean[] {false, true}))));
	                  break;
	
	              case "4":
	                  cameraServer.SetConfig(new VisionMessageConfig(0,1,
	                          new ArrayList<>(Arrays.asList(new Boolean[] {true, true}))));
	                  break;
	
	              default:
	                  cameraServer.SetConfig(new VisionMessageConfig(1,0,
	                          new ArrayList<>(Arrays.asList(new Boolean[] {true, true}))));
	         }
	      }
      }
      finally
      {
    	  cc.close();
      }
   }
   
    public void Notify(VisionMessageTargets message)
    {
        //System.out.println(message.toString());
    }
}
