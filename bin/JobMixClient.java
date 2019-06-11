import lia.Monitor.JiniClient.Store.Main;

import lia.Monitor.monitor.monPredicate;
import lia.Monitor.monitor.Result;
import lia.Monitor.monitor.eResult;
import lia.Monitor.monitor.ExtResult;
import lia.Monitor.monitor.AccountingResult;
import lia.Monitor.monitor.ShutdownReceiver;
import lia.util.ShutdownManager;

import lia.Monitor.monitor.DataReceiver;

import lia.Monitor.monitor.MFarm;

import lia.Monitor.DataCache.DataSelect;

import lia.Monitor.Store.TransparentStoreFast;
import lia.Monitor.Store.TransparentStoreFactory;

import java.io.File;
import java.io.PrintWriter;
import java.io.FileOutputStream;
import java.io.PrintStream;
import java.io.IOException;
import java.util.Vector;
import java.util.Arrays;
import java.util.Map;
import java.util.HashMap;
import java.util.Hashtable;

public class JobMixClient {

    public static void main(String args[]){

    String ofile = null;
    String cluster = null;
    for (int i = 0; i < args.length; i++) {
        if( args[i].equals("-o") ){
            ofile = args[i+1];
        } else if (args[i].equals("-c")){
            cluster = args[i+1];
        }
    }
    if(cluster == null){
        System.out.println("No cluster requested");
        System.exit(0);
    }
    String [] clusters = cluster.split(":");

	// start the repository service
	final Main jClient = new Main();
	
	// register a MyDataReceiver object to receive any new information.  The implementation below:
    //      writes the set of values as json string lines to a file ".tmp".
    //      then it overwrites target file ("mv") each loop
	// to change the behaviour either implement a similar receiver or modify the addResult() methods below
	jClient.addDataReceiver(new MyDataReceiver(ofile,clusters.length));
	
    // just a simple mapping for EOS naming different than cluster ... not used this example
    final Hashtable<String,String> EOS_hash = new Hashtable<String,String>(){{
            put("LBL", "LBL");
            put("ORNL","ORNL");
            put("HPCS","LBL_HPCS");
	}};

	// dynamically subscribe to some interesting parameters
	// it can be done in the code or in ../conf/App.properties in this configuration key:
	//       lia.Monitor.JiniClient.Store.predicates=

    int c_check=0;
    for (int i=0; i<clusters.length; i++){
            jClient.registerPredicate(new monPredicate(clusters[i], "Site_UserJobs_Summary", "*", -1, -1, new String[]{"count","cpu_time","run_time","rss","virtualmem","workdir_size"}, null));
            c_check+=1;
            //System.out.println("Adding new predicate for "+clusters[i]);
    }

    if(c_check == 0){
        System.out.println("No cluster request found");
        System.exit(0);
    }

}
    
    /**
     * This is a very simple data receiver that puts some filters on the received data
     * and outputs the matching values on the console.
     */ 
    private static class MyDataReceiver implements DataReceiver, ShutdownReceiver {
	
	public MyDataReceiver(String outfile, int numberOfClusters) {

        StringBuilder sb = new StringBuilder();
        sb.append(outfile+".tmp");
        moutfile=sb.toString();
        StringBuilder sb2 = new StringBuilder();
        sb2.append("mv "+moutfile+" "+outfile);
        mvcmd = sb2.toString();
        nClusters = numberOfClusters;
	}
	
    private String currentCluster = "None";
    private String mvcmd = null;
    private String moutfile = null;
	private FileOutputStream lastFile = null;
	
    private PrintStream fs = null;

	private long lastRotated = 0;
    private int currentCount = 0;
    private int nClusters = 0;

	public void Shutdown(){
	    System.out.flush();
	}

    // here we copy 'tmp' file to real file (if tmp file exists) and open new outfile stream. Reset currentCount 
    private void resetStream(){

        // System.out.println("Resetting Stream with number of clusters ="+nClusters+" and currentCount="+currentCount);
        currentCount = 1;
        try {
            if( lastFile != null){ 
                lastFile.close(); 
                Runtime r = Runtime.getRuntime();
                Process p = r.exec(mvcmd);
                try {
                    p.waitFor();
                }
                catch (Exception ex){
                    System.err.println(ex.getMessage());
                }
            }
            lastFile = new FileOutputStream(moutfile,false);
            fs = new PrintStream(lastFile);
        }
        catch (final IOException ioe){
            System.err.println(ioe.getMessage());
        }

    }

    // write the line
	private void logLine(final String line) throws IOException {
        if( lastFile == null ){
            System.out.println("No outfile open? " +line);
	        System.out.flush();
        } else {
            fs.println(line);
            fs.flush();
        }
	}

    private Boolean checkClusters(final long elapsed){
        //System.out.println("In checkCluster with time elapsed="+elapsed);
        // count will go over nClusters once every cluster is done.... anyway, if it's been more than ~15 minutes (1000 seconds), write the file
        if((nClusters == 1 && elapsed > 10000) || (currentCount>nClusters) || (elapsed > 1000000) ) {
            return true;
        }
        return false;
    }


    private void checkToResetStream(final long timestamp){
        long elapsed = timestamp - lastRotated;
        if ( (lastRotated == 0) || (checkClusters(elapsed))){
            resetStream();
            lastRotated = timestamp;
        }
    }

    // this is from original example where each parameter is a line.  In the current example - see addResult(Result r) - all paramamgers per Node are on 1 line
    // and the 'logResult' method is not used.  I keep it here as an alternate example
	private void logResult(final long timestamp, final String farm, final String cluster, final String node, final String parameter, final String value){
        try{
		logLine("{\"timestamp\":"+timestamp+",\"Farm\":\""+farm+"\", \"Cluster\":\""+cluster+"\",\"Node\":\""+node+"\",\""+parameter+"\":\""+value+"\"}");
	    }
	    catch (final IOException ioe){
		System.err.println(ioe.getMessage());
	    }
	}
	
	public void addResult(eResult r){
	    // this is where injecting the received data in the target database should be done instead of logging it in a file
	    for (int i=0; i<r.param.length; i++)
		logResult(r.time, r.FarmName, r.ClusterName, r.NodeName, r.param_name[i], r.param[i].toString());
        
    }

    // where most of the work happens
	public void addResult(Result r){
        // System.out.println("in add result for " + r.FarmName);

        // increment currentCount with each new cluster
        if(!currentCluster.equals(r.FarmName)){
            currentCluster = r.FarmName;
            currentCount +=1;
        }
        checkToResetStream(r.time);

        StringBuilder sb = new StringBuilder();
        sb.append("{\"Farm\":\""+r.FarmName+"\",\"Node\":\""+r.NodeName+"\"");
        for (int i=0; i<r.param.length; i++)
            sb.append(",\""+r.param_name[i]+"\":\""+String.format("%f", r.param[i])+"\"");

        sb.append("}");
        String s = sb.toString();
        try {
            logLine(s);
        }
        catch (final IOException ioe){
            System.err.println(ioe.getMessage());
        }
    }
	
	public void addResult(ExtResult er){
	}
	
	public void addResult(AccountingResult ar){
	}
	
	public void updateConfig(MFarm f){
	}
    }
}
