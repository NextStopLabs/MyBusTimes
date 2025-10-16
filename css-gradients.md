# How to make a CSS livery

## 1. Basic CSS gradients

### 1.1 Straight lines (2 colours)

The most basic for of CSS gradients is the linear gradient

example:<br>
```CSS
linear-gradient(#ffffff 50%, #000000 50%)
```

brakedown:<br>
```
linear-gradient :This is the type of gradient:
(
    #ffffff 50%, :Defining the colour #ffffff from 0% to 50%:
    #000000 50%  :Defining the colour #000000 from 50% to 100%:
)
```

We dont need to add 0% or 100% to these because it is just the 2 colours.

### 1.2 More Colours
If we add a 3rd colour we would need to define where that colour starts and where it ends.

brakedown:<br>
```
linear-gradient :This is the type of gradient:
(
    #ffffff 45%, :Defining the colour #ffffff from 0% to 45%:
    #ff0000 45% 55%, :Defining the colour #ff0000 from 45% 55%:
    #000000 55%  :Defining the colour #000000 from 55% to 100%:
)
```

Here we have to tell it that we want the colour #ff0000 to start at 45% and go until 55%.

### 1.3 Stacking Gradients
We can also stack gradients to create diffrent shapes.

Example: