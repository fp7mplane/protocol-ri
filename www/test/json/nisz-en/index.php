<?php 
if(!empty($_POST) && $_POST!=null){
	$_GET = $_POST;
}

header("Cache-Control: no-store, no-cache, must-revalidate, max-age=0");
header("Cache-Control: post-check=0, pre-check=0", false);
header("Pragma: no-cache");

	if(!empty($_GET['objectId']) && $_GET['objectId']!=null){
		
			$file = fopen($_GET['objectId']."-def.json", "r");	
			echo fread ($file, filesize($_GET['objectId']."-def.json"));
			fclose ($file);
			exit;
	}
?>
