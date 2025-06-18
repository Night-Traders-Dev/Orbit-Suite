from blockchain.tokenutil import send_orbit

result = send_orbit("ORB.464409AB4319F07483CB2E32", "ORB.5A9F73B26D469D3DDF221F1D", 10000, order="Bug Bounty")
if "success" in result:
    print("Reward Sent")
