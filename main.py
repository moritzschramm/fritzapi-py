import fritzapi


if fritzapi.login():

    print(fritzapi.get_devices())

    fritzapi.logout()
