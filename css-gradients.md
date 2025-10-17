# How to make a CSS livery

## 1. Basic CSS gradients

### 1.1 Straight lines (2 colours)

The most basic for of CSS gradients is the linear gradient

example:<br>
```CSS
linear-gradient(#ffffff 50%, transparent00 50%)
```

brakedown:<br>
```CSS
linear-gradient  /*This is the type of gradient*/
(
    #ffffff 50%, /*Defining the colour #ffffff from 0% to 50%*/
    transparent00 50%  /*Defining the colour transparent00 from 50% to 100%*/
)
```

We dont need to add 0% or 100% to these because it is just the 2 colours.

### 1.2 More Colours
If we add a 3rd colour we would need to define where that colour starts and where it ends.

brakedown:<br>
```CSS
linear-gradient      /*This is the type of gradient*/
(
    #ffffff 45%,     /*Defining the colour #ffffff from 0% to 45%*/
    #ff0000 45% 55%, /*Defining the colour #ff0000 from 45% 55%*/
    transparent00 55%      /*Defining the colour transparent00 from 55% to 100%*/
)
```

Here we have to tell it that we want the colour #ff0000 to start at 45% and go until 55%.

### 1.3 Stacking Gradients
We can also stack gradients to create diffrent shapes.

Example:
```CSS
linear-gradient(to bottom, transparent 45%, #ff0000 45% 65%, transparent 65%),
linear-gradient(to left, #ffffff 45%, #ff0000 45% 55%, #ffffff 55%)
```

Here we are stacking two gradents

Breakdown:
```CSS
linear-gradient
(
    to bottom,         /*Define the direction of the gradient*/
    transparent 45%,   /*Define the first 45% to be transparent you can also use #0000*/
    #ff0000 45% 65%,   /*Define 45% to 65% to be #ff0000 (red)*/
    transparent 65%.   /*Define the final 65% to 100% as transparent*/
),                     /*added a , here allows us to add another gradient*/

linear-gradient
(
    to left,           /*Define the direction of the gradient*/
    #ffffff 45%,       /*Define the colour #ffffff from 0% to 45%*/
    #ff0000 45% 55%,   /*Define the colour #ff0000 from 45% to 55%*/
    #ffffff 55%.       /*Define the colour #ffffff from 55% to 100%*/
)
```

Here we use a , to start two CSS gradients on top of each other.<br>
We use transparent / #0000 to allow the other gradient underneath to show.

### 1.4 Gradient directions

With CSS gradients we have 2 main options for defining there there directions

1. We can use terms such as "to top", "to bottom", "to top left"
2. We can also define a spacfic angle be using "20deg", This allows us to set it to any angle we want

## 2. Radial Gradients

2.1 Radial gradients allow us to make ellipse and circles and can stacked in the same way as a linear gradient.<br>
You can also stack any type of gradient on top of any other types

Example:
```CSS
radial-gradient(circle, red 30%, yellow 30% 40%, green 40%)
```