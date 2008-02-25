<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<?python import sitetemplate ?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#" py:extends="sitetemplate">

<head py:match="item.tag=='{http://www.w3.org/1999/xhtml}head'" py:attrs="item.items()">
    <meta content="text/html; charset=UTF-8" http-equiv="content-type" py:replace="''"/>
    <title py:replace="''">Your title goes here</title>
    <meta py:replace="item[:]"/>
    <style type="text/css">
        #pageLogin
        {
            font-size: 10px;
            font-family: verdana;
            text-align: right;
        }
    </style>
    <style type="text/css" media="screen">
@import "${tg.url('/static/css/style.css')}";
</style>
    <script type="text/javascript"
    src="/static/javascript/MochiKit/MochiKit.js"></script>
    <script type="text/javascript"
    src="/static/javascript/hideshow/hs.js"></script>
    <script type="text/javascript"
    src="/static/javascript/tabber.js"></script>
    <script type="text/javascript"
    src="/static/javascript/resize_textarea/resizable_textareas.js"></script>	    




</head>

<body py:match="item.tag=='{http://www.w3.org/1999/xhtml}body'" py:attrs="item.items()">

    <div id="header">
<div id="menu">
      <ul>
	<li>[<a href="/">home</a>]</li>
	<li>[<a href="/cookbook/">cookbook</a>]</li>
      </ul>
<div id="search">
  logged in as ${tg.user.uni} [<a href="/logout">logout</a>]
</div>
    </div>
</div>
    <div id="main_content">
    
    <div id="status_block" class="flash" py:if="value_of('tg_flash', None)" py:content="tg_flash"></div>

    <div py:replace="[item.text]+item[:]"/>

    <!-- End of main_content -->
    </div>
<div id="footer"> 
</div>
</body>

</html>
