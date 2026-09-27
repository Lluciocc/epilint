int strleh(char *s)
{
    return *s ? strleh(s + 1) + 1 : 0;
}
